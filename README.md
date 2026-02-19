# ✂️ BarberSync

**BarberSync** is a lightweight, full-stack appointment management system designed for local barbers to streamline their scheduling process. This project replaces manual booking with an automated, user-friendly web interface, reducing administrative overhead and scheduling conflicts.

## 🌐 Live Demo
The application is currently deployed on **Render**. 
**[View Live Project](https://barbersync.onrender.com)** *(Note: Free tier instances may take a moment to spin up if inactive)*.

---

## 🌟 Key Features
* **Instant Booking**: Clients can view available time slots and book appointments in seconds without needing an account.
* **Admin Dashboard**: A secure backend for barbers to manage their schedule, view customer details, and manually lock time slots for breaks.
* **Automated Validation**: Built-in logic to prevent double-booking and ensure time-slot integrity.
* **Responsive Design**: Fully optimized for mobile and desktop browsers using Jinja2 templates and CSS.

## 🛠️ Tech Stack
* **Language**: Python 3.10+
* **Framework**: FastAPI (Asynchronous Backend)
* **Database**: SQLite with SQLAlchemy ORM
* **Templating**: Jinja2
* **Deployment**: Render (Cloud Infrastructure)

---

## 🚀 Local Development

### Prerequisites
* Python 3.10 or higher
* Git

### Installation
1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/DEM-YU/barbersync.git](https://github.com/DEM-YU/barbersync.git)
    cd barbersync
    ```

2.  **Set up a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application**:
    ```bash
    uvicorn main:app --reload
    ```
    The site will be available at `http://127.0.0.1:8000`.

---

## 👨‍💻 About the Author
**Brooks (Ximing) Yu** *First-year Computer Science Honours Student at the University of Alberta*.

I am a backend-focused developer with a strong interest in cloud computing, AI-assisted programming (Vibe Coding), and entrepreneurship. This project was built as part of my portfolio for **Summer 2026 Internship** applications.

* **GitHub**: [DEM-YU](https://github.com/DEM-YU)
* **Interests**: Distributed Systems, Backend Architecture, and Economic Data Visualization.

---
*Developed with a focus on clean code and scalable architecture.*
