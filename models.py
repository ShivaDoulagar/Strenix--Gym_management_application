from datetime import datetime
from flask_login import UserMixin
from db import db

# Association table for many-to-many between WorkoutPlan and Exercise
workout_exercises = db.Table('workout_exercises',
    db.Column('workout_id', db.Integer, db.ForeignKey('workout_plan.id')),
    db.Column('exercise_id', db.Integer, db.ForeignKey('exercise.id'))
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    role = db.Column(db.String(20), default='user')  # 'user' or 'admin'
    goals = db.Column(db.String(255))  # e.g., 'weight loss', 'muscle gain'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    workout_plans = db.relationship('WorkoutPlan', backref='creator', lazy=True)
    nutrition_logs = db.relationship('NutritionLog', backref='user', lazy=True)
    progress_logs = db.relationship('Progress', backref='user', lazy=True)


class WorkoutPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    level = db.Column(db.String(50))  # beginner, intermediate, advanced
    description = db.Column(db.Text)
    duration = db.Column(db.Integer, nullable=True)  # Add duration field in minutes
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    date = db.Column(db.Date, nullable=True)  # Add date field for scheduling workouts
    progress = db.Column(db.Integer, default=0)  # Add progress field (0-100)
    calories = db.Column(db.Integer, nullable=True)  # Add calories field

    exercises = db.relationship('Exercise', secondary=workout_exercises, backref='plans')


class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    video_url = db.Column(db.String(255))
    muscle_group = db.Column(db.String(50))
    # Add these fields to match your app.py usage
    sets = db.Column(db.Integer, nullable=True)
    reps = db.Column(db.String(20), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    workout_plan_id = db.Column(db.Integer, nullable=True)  # For direct relationship


class NutritionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date)
    meal = db.Column(db.String(100))
    calories = db.Column(db.Float)
    protein = db.Column(db.Float)
    carbs = db.Column(db.Float)
    fats = db.Column(db.Float)


class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date)
    weight = db.Column(db.Float)
    body_fat_percentage = db.Column(db.Float)
    notes = db.Column(db.Text)