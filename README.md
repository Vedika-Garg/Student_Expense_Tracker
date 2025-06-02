# Student Expense Tracker

A comprehensive web application for students to track their expenses, manage funds, and visualize spending patterns.

## Features

- User authentication (login/signup)
- Expense tracking with categories
- Fund addition tracking
- Visualizations (pie charts, bar charts, line charts)
- Daily spending recommendations
- Monthly savings tracking
- Dark/light mode toggle
- Responsive design

## Tech Stack

- Backend: Python (Flask)
- Database: MySQL
- Frontend: HTML, CSS, JavaScript
- Data Visualization: Matplotlib

## Project Structure

\`\`\`
student-expense-tracker/
├── app.py                  # Main Flask application
├── schema.sql              # Database schema
├── templates/              # HTML templates
│   ├── index.html          # Landing page
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   └── dashboard.html      # Main dashboard
├── static/                 # Static assets
│   ├── css/                # CSS stylesheets
│   │   └── styles.css      # Main stylesheet
│   ├── js/                 # JavaScript files
│   │   └── script.js       # Main JavaScript file
│   └── images/             # Images
│       └── logo.png        # Application logo
└── README.md               # Project documentation
\`\`\`

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- MySQL 5.7 or higher

### Database Setup

1. Install MySQL if you haven't already
2. Create a new database:

```bash
mysql -u root -p &lt; schema.sql