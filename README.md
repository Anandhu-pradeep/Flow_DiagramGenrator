# SchemaCraft – A Code-Based ER Diagram Generator

SchemaCraft is a complete web application built with Python Django and MySQL that transforms custom schema syntax into real-time Entity Relationship (ER) diagrams using Mermaid.js.

## Prerequisites
- Python 3.8+
- MySQL Server (running on localhost:3306)
- MySQL Database named `schemacraft_db`

## Getting Started

### 1. Database Setup
Create the MySQL database:
```sql
CREATE DATABASE schemacraft_db;
```

### 2. Install Dependencies
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 3. Migrations
Prepare and apply the database schema:
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Create Superuser (Optional)
To access the Django admin:
```bash
python manage.py createsuperuser
```

### 5. Run the Server
Launch the development server:
```bash
python manage.py runserver
```

Open your browser and navigate to `http://127.0.0.1:8000/`.

## Custom Syntax Example
In the project editor, you can write:

```text
Entity User {
  id int pk
  username string
  email string
}

Entity Project {
  id int pk
  title string
  user_id int fk
}

Relationship User -> Project (1:N)
```

The system will automatically generate a corresponding Mermaid.js ER diagram preview.

## Features
- **User Authentication:** Sign up and log in to manage your projects.
- **CRUD Operations:** Create, edit, and delete ER projects.
- **Live Preview:** Real-time diagram rendering as you type.
- **Smart Parser:** Robust extraction of entities, attributes, and cardinality.
- **Premium UI:** Dark-themed, responsive dashboard and editor.
