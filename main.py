from fastapi import FastAPI, Request, Form, Depends, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from database import SessionLocal, engine, Appointment, init_db
import hashlib
import re
import os

# 启动时自动创建表
init_db()

# ===== 管理员配置 =====
ADMIN_PASSWORD = "123456"  # 管理员密码
ACCESS_TOKEN = hashlib.md5(ADMIN_PASSWORD.encode()).hexdigest()  # 生成token

# ===== 系统常量 =====
TZ = ZoneInfo("America/Edmonton")  # 统一时区
SYSTEM_BLOCK_PHONE = "SYSTEM_BLOCK"  # 系统锁定时间的特殊电话标识


def clean_phone(phone: str) -> str:
    """清洗手机号：去除空格、横线、括号，只保留数字"""
    return re.sub(r'[^0-9]', '', phone)

app = FastAPI()

# 动态获取templates目录路径，兼容本地和服务器环境
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    """首页 - 渲染可视化时间表"""
    
    # 获取当前日期（不含时间）- 使用统一时区
    now = datetime.now(TZ)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    
    # 生成未来5天的日期列表
    days = []
    for i in range(5):
        day = today + timedelta(days=i)
        days.append({
            "date": day.strftime("%Y-%m-%d"),
            "display": day.strftime("%m/%d"),
            "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][day.weekday()]
        })
    
    # 生成时间段列表 (08:00 - 20:00, 每30分钟)
    time_slots = []
    for hour in range(8, 20):
        time_slots.append(f"{hour:02d}:00")
        time_slots.append(f"{hour:02d}:30")
    
    # 查询未来5天内的所有已预约时段
    end_date = today + timedelta(days=6)
    existing_appointments = db.query(Appointment).filter(
        Appointment.start_time >= today,
        Appointment.start_time < end_date
    ).all()
    
    # 将已预约时段转换为 "YYYY-MM-DD HH:MM" 格式的列表
    booked_slots = []
    for appt in existing_appointments:
        slot_key = appt.start_time.strftime("%Y-%m-%d %H:%M")
        booked_slots.append(slot_key)
    
    # 获取当前时间，用于前端判断过期时段 - 使用统一时区
    current_time = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "days": days,
        "time_slots": time_slots,
        "booked_slots": booked_slots,
        "current_time": current_time
    })


@app.post("/book")
async def book_appointment(
    name: str = Form(...),
    phone: str = Form(...),
    time: str = Form(...),
    db: Session = Depends(get_db)
):
    """处理预约提交"""
    # 0. 清洗手机号
    phone = clean_phone(phone)
    
    # 1. 解析时间 (格式: YYYY-MM-DD HH:MM)
    appt_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
    
    # 2. 禁止穿越预约：不能预约过去的时间
    now = datetime.now(TZ).replace(tzinfo=None)
    if appt_time < now:
        print(f"⚠️ 拒绝穿越预约: {name} 试图预约 {time}")
        return RedirectResponse(url="/?error=past", status_code=303)
    
    # 3. 检查时间冲突
    existing_appt = db.query(Appointment).filter(
        Appointment.start_time == appt_time
    ).first()
    
    if existing_appt:
        print(f"⚠️ 拦截冲突: {name} 想要预约 {time}，但被占了！")
        return RedirectResponse(url="/?error=conflict", status_code=303)
    
    # 4. 创建新预约
    new_appt = Appointment(customer_name=name, phone=phone, start_time=appt_time)
    db.add(new_appt)
    db.commit()
    
    print(f"🎉 新订单写入: {name} - {time}")
    return RedirectResponse(url="/?success=true", status_code=303)


@app.post("/user-cancel")
async def user_cancel_appointment(
    name: str = Form(...),
    phone: str = Form(...),
    time: str = Form(...),
    db: Session = Depends(get_db)
):
    """用户自助取消预约"""
    # 0. 清洗手机号
    phone = clean_phone(phone)
    
    # 1. 解析时间
    try:
        appt_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
    except ValueError:
        return RedirectResponse(url="/?error=invalid", status_code=303)
    
    # 2. 查找该时间的预约
    appt = db.query(Appointment).filter(
        Appointment.start_time == appt_time
    ).first()
    
    if not appt:
        return RedirectResponse(url="/?error=not_found", status_code=303)
    
    # 3. 系统锁定的时间不允许用户取消
    if appt.phone == SYSTEM_BLOCK_PHONE:
        return RedirectResponse(url="/?error=auth_failed", status_code=303)
    
    # 4. 验证身份（姓名和电话必须匹配）
    if appt.customer_name == name and appt.phone == phone:
        db.delete(appt)
        db.commit()
        print(f"🗑️ 用户自行取消预约: {name} - {time}")
        return RedirectResponse(url="/?success=cancelled", status_code=303)
    else:
        print(f"⚠️ 取消验证失败: 输入 {name}/{phone}，记录 {appt.customer_name}/{appt.phone}")
        return RedirectResponse(url="/?error=auth_failed", status_code=303)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: bool = False):
    """登录页面"""
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.post("/login")
async def login(password: str = Form(...)):
    """验证登录"""
    if password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="access_token", value=ACCESS_TOKEN, httponly=True)
        print("🔓 管理员登录成功")
        return response
    else:
        print("🔒 登录失败：密码错误")
        return RedirectResponse(url="/login?error=true", status_code=303)


@app.get("/logout")
async def logout():
    """退出登录"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
    print("🔒 管理员已退出登录")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, date: str = None, db: Session = Depends(get_db)):
    """理发师后台看板（需要登录）"""
    
    # 验证登录状态
    token = request.cookies.get("access_token")
    if token != ACCESS_TOKEN:
        return RedirectResponse(url="/login", status_code=303)
    
    # 解析日期参数，默认为今天 - 使用统一时区
    now = datetime.now(TZ)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    if date:
        try:
            selected_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            selected_date = today
    else:
        selected_date = today
    
    # 计算日期范围
    next_day = selected_date + timedelta(days=1)
    
    # 查询选定日期的预约
    appointments = db.query(Appointment).filter(
        Appointment.start_time >= selected_date,
        Appointment.start_time < next_day
    ).order_by(Appointment.start_time.asc()).all()
    
    # 统计：今日预约数
    today_start = today
    today_end = today + timedelta(days=1)
    today_count = db.query(Appointment).filter(
        Appointment.start_time >= today_start,
        Appointment.start_time < today_end
    ).count()
    
    # 统计：本周预约数
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=7)
    week_count = db.query(Appointment).filter(
        Appointment.start_time >= week_start,
        Appointment.start_time < week_end
    ).count()
    
    # 生成日期选择器的日期列表（今天及未来6天）
    date_options = []
    for i in range(7):
        d = today + timedelta(days=i)
        date_options.append({
            "date": d.strftime("%Y-%m-%d"),
            "display": d.strftime("%m/%d"),
            "weekday": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][d.weekday()],
            "is_today": i == 0
        })
    
    return templates.TemplateResponse(
        "dashboard.html", 
        {
            "request": request, 
            "appointments": appointments,
            "selected_date": selected_date.strftime("%Y-%m-%d"),
            "selected_display": selected_date.strftime("%m月%d日"),
            "today_count": today_count,
            "week_count": week_count,
            "date_options": date_options
        }
    )


@app.post("/cancel/{appointment_id}")
async def cancel_appointment(request: Request, appointment_id: int, db: Session = Depends(get_db)):
    """取消预约（需要登录）"""
    # 验证登录状态
    token = request.cookies.get("access_token")
    if token != ACCESS_TOKEN:
        return RedirectResponse(url="/login", status_code=303)
    
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if appt:
        db.delete(appt)
        db.commit()
        print(f"🗑️ 预约已取消: ID={appointment_id}")
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/block-time")
async def block_time(
    request: Request,
    time: str = Form(...),
    db: Session = Depends(get_db)
):
    """理发师锁定/休息时间（需要登录）"""
    # 验证登录状态
    token = request.cookies.get("access_token")
    if token != ACCESS_TOKEN:
        return RedirectResponse(url="/login", status_code=303)
    
    # 解析时间
    try:
        block_time = datetime.strptime(time, "%Y-%m-%d %H:%M")
    except ValueError:
        return RedirectResponse(url="/dashboard?error=invalid", status_code=303)
    
    # 检查该时间是否已被占用
    existing = db.query(Appointment).filter(
        Appointment.start_time == block_time
    ).first()
    
    if existing:
        return RedirectResponse(url="/dashboard?error=conflict", status_code=303)
    
    # 创建系统锁定的特殊预约
    block_appt = Appointment(
        customer_name="⛔️ 休息中",
        phone=SYSTEM_BLOCK_PHONE,
        start_time=block_time
    )
    db.add(block_appt)
    db.commit()
    
    print(f"🔒 时间段已锁定: {time}")
    return RedirectResponse(url="/dashboard?success=blocked", status_code=303)


# ===== 本地开发入口 =====
# 只有直接运行 python main.py 时才启动 uvicorn
# PythonAnywhere 的 WSGI 会通过其他方式导入 app，不会触发这个块
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)