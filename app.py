from flask import Flask, render_template, redirect, url_for, request, flash, send_file, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta  # Correct import for timedelta
from db import db  # This assumes your db is initialized in db.py
from models import User, WorkoutPlan, Exercise, NutritionLog, Progress  # Your model definitions
import csv
import io
from sqlalchemy import func, extract
import os
from dotenv import load_dotenv
import cv2
import mediapipe as mp
import numpy as np
import json


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness_app.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='sha256')
        name = request.form['name']
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        new_user = User(email=email, password=password, name=name)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful, please log in')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's nutrition logs for today
    today = datetime.now().date()
    today_logs = NutritionLog.query.filter_by(
        user_id=current_user.id,
        date=today
    ).all()
    
    # Calculate today's totals
    total_calories = sum(log.calories for log in today_logs)
    total_protein = sum(log.protein for log in today_logs)
    total_carbs = sum(log.carbs for log in today_logs)
    total_fats = sum(log.fats for log in today_logs)
    
    # Get today's workout plan
    today_workout = WorkoutPlan.query.filter(
        WorkoutPlan.created_by == current_user.id,
        WorkoutPlan.date == today
    ).first()
    
    if not today_workout:
        # Create a default workout if none exists
        today_workout = {
            "name": "No workout planned",
            "duration": 0,
            "calories": 0,
            "progress": 0,
            "workout_id": None
        }
    else:
        today_workout = {
            "name": today_workout.title,
            "duration": today_workout.duration,
            "calories": today_workout.calories or 0,
            "progress": today_workout.progress,
            "workout_id": today_workout.id
        }
    
    # Get recent workouts
    recent_workouts = WorkoutPlan.query.filter_by(
        created_by=current_user.id
    ).order_by(WorkoutPlan.created_at.desc()).limit(5).all()
    
    # Get latest progress
    latest_progress = Progress.query.filter_by(
        user_id=current_user.id
    ).order_by(Progress.date.desc()).first()
    
    # Calculate weight change
    weight_change = 0
    if latest_progress:
        month_ago = today - timedelta(days=30)
        old_progress = Progress.query.filter(
            Progress.user_id == current_user.id,
            Progress.date <= month_ago
        ).order_by(Progress.date.desc()).first()
        
        if old_progress:
            weight_change = latest_progress.weight - old_progress.weight
    
    # Get weekly stats
    week_ago = today - timedelta(days=7)
    calories_burned_week = WorkoutPlan.query.filter(
        WorkoutPlan.created_by == current_user.id,
        WorkoutPlan.date >= week_ago,
        WorkoutPlan.progress == 100
    ).with_entities(func.sum(WorkoutPlan.calories)).scalar() or 0
    
    workouts_completed = WorkoutPlan.query.filter(
        WorkoutPlan.created_by == current_user.id,
        WorkoutPlan.date >= week_ago,
        WorkoutPlan.progress == 100
    ).count()
    
    # Get weekly goals
    weekly_goals = [
        {"name": "Workouts", "current": workouts_completed, "target": 5},
        {"name": "Calories Burned", "current": calories_burned_week, "target": 2000}
    ]
    
    # Calculate streak
    streak = 0
    current_date = today
    while True:
        workout = WorkoutPlan.query.filter(
            WorkoutPlan.created_by == current_user.id,
            WorkoutPlan.date == current_date,
            WorkoutPlan.progress == 100
        ).first()
        
        if not workout:
            break
            
        streak += 1
        current_date -= timedelta(days=1)
    
    # Daily calorie goal (placeholder)
    daily_calorie_goal = 2400
    
    return render_template(
        'dashboard.html',
        user=current_user,
        total_calories=total_calories,
        total_protein=total_protein,
        total_carbs=total_carbs,
        total_fats=total_fats,
        daily_calorie_goal=daily_calorie_goal,
        recent_workouts=recent_workouts,
        latest_progress=latest_progress,
        weight_change=weight_change,
        calories_burned_week=calories_burned_week,
        workouts_completed=workouts_completed,
        weekly_goals=weekly_goals,
        streak=streak,
        today_workout=today_workout
    )

@app.route('/workout_plans')
@login_required
def workout_plans():
    plans = WorkoutPlan.query.filter_by(created_by=current_user.id).all()
    return render_template('workout_plans.html', plans=plans)

@app.route('/workout_plans/<int:id>')
@login_required
def workout_plan(id):
    plan = WorkoutPlan.query.get_or_404(id)
    return render_template('workout_plan.html', plan=plan)

# @app.route('/nutrition_logs')
# @login_required
# def nutrition_logs():
#     logs = NutritionLog.query.filter_by(user_id=current_user.id).all()
#     return render_template('nutrition_logs.html', logs=logs)

@app.route('/progress_logs')
@login_required
def progress_logs():
    logs = Progress.query.filter_by(user_id=current_user.id).all()
    return render_template('progress_logs.html', logs=logs)

@app.route('/nutrition_logs')
@login_required
def nutrition_logs():
    # Get filter parameters
    date_range = request.args.get('date_range', '30')  # Default to last 30 days
    meal_type = request.args.get('meal_type', 'all')
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of logs per page
    
    # Base query
    query = NutritionLog.query.filter_by(user_id=current_user.id)
    
    # Apply date filter
    if date_range != 'all':
        days = int(date_range)
        start_date = datetime.now().date() - timedelta(days=days)
        query = query.filter(NutritionLog.date >= start_date)
    
    # Apply meal type filter
    if meal_type != 'all':
        query = query.filter(NutritionLog.meal == meal_type)
    
    # Apply search filter
    if search:
        query = query.filter(NutritionLog.meal.ilike(f'%{search}%'))
    
    # Calculate averages for the summary stats
    # First, get the unique dates in the filtered set
    date_subquery = query.with_entities(NutritionLog.date).distinct().subquery()
    
    # Calculate daily averages
    avg_calories = db.session.query(func.avg(
        db.session.query(func.sum(NutritionLog.calories))
        .filter(NutritionLog.user_id == current_user.id, NutritionLog.date == date_subquery.c.date)
        .group_by(NutritionLog.date)
        .scalar_subquery()
    )).scalar()
    
    avg_protein = db.session.query(func.avg(
        db.session.query(func.sum(NutritionLog.protein))
        .filter(NutritionLog.user_id == current_user.id, NutritionLog.date == date_subquery.c.date)
        .group_by(NutritionLog.date)
        .scalar_subquery()
    )).scalar()
    
    avg_carbs = db.session.query(func.avg(
        db.session.query(func.sum(NutritionLog.carbs))
        .filter(NutritionLog.user_id == current_user.id, NutritionLog.date == date_subquery.c.date)
        .group_by(NutritionLog.date)
        .scalar_subquery()
    )).scalar()
    
    avg_fats = db.session.query(func.avg(
        db.session.query(func.sum(NutritionLog.fats))
        .filter(NutritionLog.user_id == current_user.id, NutritionLog.date == date_subquery.c.date)
        .group_by(NutritionLog.date)
        .scalar_subquery()
    )).scalar()
    
    # Order by date (most recent first) and paginate results
    pagination = query.order_by(NutritionLog.date.desc(), NutritionLog.id.desc()).paginate(page=page, per_page=per_page)
    logs = pagination.items
    
    return render_template(
        'nutrition_logs.html',
        logs=logs,
        pagination=pagination,
        avg_calories=avg_calories,
        avg_protein=avg_protein,
        avg_carbs=avg_carbs,
        avg_fats=avg_fats
    )


@app.route('/edit_nutrition_log/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_nutrition_log(id):
    log = NutritionLog.query.get_or_404(id)
    
    # Ensure the log belongs to the current user
    if log.user_id != current_user.id:
        flash('You do not have permission to edit this log', 'danger')
        return redirect(url_for('nutrition_logs'))
    
    if request.method == 'POST':
        log.date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        log.meal = request.form['meal']
        log.calories = float(request.form['calories'])
        log.protein = float(request.form['protein'])
        log.carbs = float(request.form['carbs'])
        log.fats = float(request.form['fats'])
        
        db.session.commit()
        flash('Nutrition log updated successfully!', 'success')
        return redirect(url_for('nutrition_logs'))
    
    return render_template('edit_nutrition_log.html', log=log)

@app.route('/delete_nutrition_log/<int:id>', methods=['POST'])
@login_required
def delete_nutrition_log(id):
    log = NutritionLog.query.get_or_404(id)
    
    # Ensure the log belongs to the current user
    if log.user_id != current_user.id:
        flash('You do not have permission to delete this log', 'danger')
        return redirect(url_for('nutrition_logs'))
    
    db.session.delete(log)
    db.session.commit()
    flash('Nutrition log deleted successfully!', 'success')
    return redirect(url_for('nutrition_logs'))

@app.route('/export_nutrition_logs')
@login_required
def export_nutrition_logs():
    # Get all logs for the current user
    logs = NutritionLog.query.filter_by(user_id=current_user.id).order_by(NutritionLog.date.desc()).all()
    
    export_format = request.args.get('format', 'csv')
    
    if export_format == 'csv':
        # Create a CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Date', 'Meal', 'Calories', 'Protein (g)', 'Carbs (g)', 'Fats (g)'])
        
        # Write data
        for log in logs:
            writer.writerow([
                log.date.strftime('%Y-%m-%d'),
                log.meal,
                log.calories,
                log.protein,
                log.carbs,
                log.fats
            ])
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'nutrition_logs_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    
    elif export_format == 'pdf':
        # This is a placeholder for PDF generation
        # You would need to install a library like fpdf or reportlab
        
        # For now, just redirect back with a message
        flash('PDF export is not implemented yet', 'warning')
        return redirect(url_for('nutrition_logs'))
    
    else:
        return redirect(url_for('nutrition_logs'))

# API endpoint for chart data
@app.route('/api/nutrition_chart_data')
@login_required
def nutrition_chart_data():
    # Get date range from query parameters
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now().date() - timedelta(days=days)
    
    # Query for daily calorie data
    daily_calories = db.session.query(
        NutritionLog.date,
        func.sum(NutritionLog.calories).label('total_calories')
    ).filter(
        NutritionLog.user_id == current_user.id,
        NutritionLog.date >= start_date
    ).group_by(NutritionLog.date).order_by(NutritionLog.date).all()
    
    # Query for macro distribution
    macro_data = db.session.query(
        func.sum(NutritionLog.protein).label('total_protein'),
        func.sum(NutritionLog.carbs).label('total_carbs'),
        func.sum(NutritionLog.fats).label('total_fats')
    ).filter(
        NutritionLog.user_id == current_user.id,
        NutritionLog.date >= start_date
    ).first()
    
    # Query for meal type breakdown
    meal_breakdown = db.session.query(
        NutritionLog.meal,
        func.sum(NutritionLog.calories).label('total_calories')
    ).filter(
        NutritionLog.user_id == current_user.id,
        NutritionLog.date >= start_date
    ).group_by(NutritionLog.meal).all()
    
    # Format the data for charts
    calorie_data = [{
        'date': entry.date.strftime('%Y-%m-%d'),
        'calories': float(entry.total_calories)
    } for entry in daily_calories]
    
    macro_distribution = {
        'protein': float(macro_data.total_protein) if macro_data.total_protein else 0,
        'carbs': float(macro_data.total_carbs) if macro_data.total_carbs else 0,
        'fats': float(macro_data.total_fats) if macro_data.total_fats else 0
    }
    
    meal_data = [{
        'meal': entry.meal,
        'calories': float(entry.total_calories)
    } for entry in meal_breakdown]
    
    return jsonify({
        'calories': calorie_data,
        'macros': macro_distribution,
        'meals': meal_data
    })


@app.route('/add_nutrition_log', methods=['GET', 'POST'])
@login_required
def add_nutrition_log():
    if request.method == 'POST':
        try:
            # Parse the form data
            date = datetime.strptime(request.form['date'], '%Y-%m-%d')
            meal = request.form['meal']
            calories = float(request.form['calories'])
            protein = float(request.form['protein'])
            carbs = float(request.form['carbs'])
            fats = float(request.form['fats'])
            
            # Create new nutrition log
            new_log = NutritionLog(
                user_id=current_user.id,
                date=date,
                meal=meal,
                calories=calories,
                protein=protein,
                carbs=carbs,
                fats=fats
            )
            
            # Save to database
            db.session.add(new_log)
            db.session.commit()
            flash('Nutrition log added successfully!', 'success')
            return redirect(url_for('nutrition_logs'))
            
        except ValueError as e:
            flash(f'Error: Invalid input format. Please check your values. {str(e)}', 'danger')
            return redirect(url_for('add_nutrition_log'))
        except Exception as e:
            flash(f'Error: An unexpected error occurred. {str(e)}', 'danger')
            db.session.rollback()
            return redirect(url_for('add_nutrition_log'))
    
    # If GET request, display the form
    # Get today's nutrition logs for the current user
    today = datetime.now().date()
    today_nutrition = NutritionLog.query.filter_by(
        user_id=current_user.id,
        date=today
    ).all()
    
    # Calculate daily totals
    daily_totals = {
        'calories': sum(log.calories for log in today_nutrition) if today_nutrition else 0,
        'protein': sum(log.protein for log in today_nutrition) if today_nutrition else 0,
        'carbs': sum(log.carbs for log in today_nutrition) if today_nutrition else 0,
        'fats': sum(log.fats for log in today_nutrition) if today_nutrition else 0
    }
    
    # Default user goals (these would normally come from user settings)
    user_goals = {
        'calories': 2000,
        'protein': 150,
        'carbs': 250,
        'fats': 70
    }
    
    return render_template(
        'add_nutrition_log.html',
        today=datetime.now(),
        daily_totals=daily_totals,
        user_goals=user_goals
    )


@app.route('/add_progress_log', methods=['GET', 'POST'])
@login_required
def add_progress_log():
    if request.method == 'POST':
        new_log = Progress(
            user_id=current_user.id,
            date=datetime.strptime(request.form['date'], '%Y-%m-%d'),
            weight=float(request.form['weight']),
            body_fat_percentage=float(request.form['body_fat_percentage']),
            notes=request.form['notes']
        )
        db.session.add(new_log)
        db.session.commit()
        return redirect(url_for('progress_logs'))
    return render_template('add_progress_log.html')




# Add these routes to your Flask application (app.py)

@app.route('/add_workout_plan', methods=['GET', 'POST'])
@login_required
def add_workout_plan():
    if request.method == 'POST':
        # Create new workout plan from form data
        new_plan = WorkoutPlan(
            title=request.form['title'],
            description=request.form['description'],
            level=request.form['level'],
            duration=int(request.form['duration']) if request.form['duration'] else None,
            created_by=current_user.id,
            created_at=datetime.now()
        )
        
        db.session.add(new_plan)
        db.session.commit()
        
        # Get the exercises from the form
        exercise_names = request.form.getlist('exercise_name[]')
        exercise_sets = request.form.getlist('exercise_sets[]')
        exercise_reps = request.form.getlist('exercise_reps[]')
        exercise_notes = request.form.getlist('exercise_notes[]')
        
        # Add exercises to the workout plan
        for i in range(len(exercise_names)):
            if exercise_names[i].strip():  # Only add if name is not empty
                # Check if exercise already exists
                existing_exercise = Exercise.query.filter_by(name=exercise_names[i]).first()
                
                if existing_exercise:
                    # Add existing exercise to the plan
                    new_plan.exercises.append(existing_exercise)
                    
                    # Update exercise attributes if needed
                    existing_exercise.sets = int(exercise_sets[i]) if exercise_sets[i] else None
                    existing_exercise.reps = exercise_reps[i]
                    existing_exercise.notes = exercise_notes[i]
                else:
                    # Create new exercise
                    new_exercise = Exercise(
                        name=exercise_names[i],
                        sets=int(exercise_sets[i]) if exercise_sets[i] else None,
                        reps=exercise_reps[i],
                        notes=exercise_notes[i],
                        workout_plan_id=new_plan.id
                    )
                    db.session.add(new_exercise)
                    new_plan.exercises.append(new_exercise)
        
        db.session.commit()
        flash('Workout plan created successfully!', 'success')
        return redirect(url_for('workout_plans'))
        
    return render_template('add_workout_plan.html')






@app.route('/edit_workout_plan/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_workout_plan(id):
    plan = WorkoutPlan.query.get_or_404(id)
    
    # Make sure the current user owns this workout plan
    if plan.created_by != current_user.id:
        flash('You do not have permission to edit this workout plan', 'danger')
        return redirect(url_for('workout_plans'))
    
    if request.method == 'POST':
        # Update workout plan from form data
        plan.title = request.form['title']
        plan.description = request.form['description']
        plan.level = request.form['level']
        plan.duration = int(request.form['duration']) if request.form['duration'] else None
        
        # Remove existing exercise associations
        plan.exercises.clear()
        
        # Get the exercises from the form
        exercise_names = request.form.getlist('exercise_name[]')
        exercise_sets = request.form.getlist('exercise_sets[]')
        exercise_reps = request.form.getlist('exercise_reps[]')
        exercise_notes = request.form.getlist('exercise_notes[]')
        
        # Add updated exercises to the workout plan
        for i in range(len(exercise_names)):
            if exercise_names[i].strip():  # Only add if name is not empty
                # Check if exercise already exists
                existing_exercise = Exercise.query.filter_by(name=exercise_names[i]).first()
                
                if existing_exercise:
                    # Add existing exercise to the plan
                    plan.exercises.append(existing_exercise)
                    
                    # Update exercise attributes if needed
                    existing_exercise.sets = int(exercise_sets[i]) if exercise_sets[i] else None
                    existing_exercise.reps = exercise_reps[i]
                    existing_exercise.notes = exercise_notes[i]
                else:
                    # Create new exercise
                    new_exercise = Exercise(
                        name=exercise_names[i],
                        sets=int(exercise_sets[i]) if exercise_sets[i] else None,
                        reps=exercise_reps[i],
                        notes=exercise_notes[i],
                        workout_plan_id=plan.id
                    )
                    db.session.add(new_exercise)
                    plan.exercises.append(new_exercise)
        
        db.session.commit()
        flash('Workout plan updated successfully!', 'success')
        return redirect(url_for('workout_plans', id=plan.id))
    
    return render_template('edit_workout_plan.html', plan=plan)





@app.route('/delete_workout_plan/<int:id>', methods=['POST'])
@login_required
def delete_workout_plan(id):
    plan = WorkoutPlan.query.get_or_404(id)
    
    # Make sure the current user owns this workout plan
    if plan.created_by != current_user.id:
        flash('You do not have permission to delete this workout plan', 'danger')
        return redirect(url_for('workout_plans'))
    
    # Clear the exercise associations
    plan.exercises.clear()
    
    # Delete the workout plan
    db.session.delete(plan)
    db.session.commit()
    
    flash('Workout plan deleted successfully!', 'success')
    return redirect(url_for('workout_plans'))

@app.route('/pose-detection')
@login_required
def pose_detection():
    return render_template('pose_detection.html')

if __name__ == '__main__':
    app.run(debug=True)