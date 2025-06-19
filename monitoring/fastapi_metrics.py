from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_fastapi_instrumentator.metrics import Info as InfoMetric
import time

# Custom metrics for your FastAPI app
app_info = Info('fastapi_app_info', 'FastAPI application info')
app_info.info({
    'app_name': 'GlowTrack API',
    'version': '1.0.0',
    'description': 'Skin care tracking application'
})

# Business metrics
user_registrations = Counter('user_registrations_total', 'Total number of user registrations')
user_logins = Counter('user_logins_total', 'Total number of user logins')
image_predictions = Counter('image_predictions_total', 'Total number of image predictions')
routine_completions = Counter('routine_completions_total', 'Total number of routine completions')

# Database metrics
db_connections = Gauge('database_connections_active', 'Active database connections')
db_query_duration = Histogram('database_query_duration_seconds', 'Database query duration')

# AI/ML metrics
prediction_accuracy = Histogram('prediction_accuracy_score', 'Prediction accuracy scores')
model_inference_time = Histogram('model_inference_duration_seconds', 'Model inference time')

def increment_user_registration():
    """Increment user registration counter"""
    user_registrations.inc()

def increment_user_login():
    """Increment user login counter"""
    user_logins.inc()

def increment_image_prediction():
    """Increment image prediction counter"""
    image_predictions.inc()

def increment_routine_completion():
    """Increment routine completion counter"""
    routine_completions.inc()

def record_db_query_time(duration: float):
    """Record database query duration"""
    db_query_duration.observe(duration)

def record_prediction_accuracy(score: float):
    """Record prediction accuracy score"""
    prediction_accuracy.observe(score)

def record_model_inference_time(duration: float):
    """Record model inference time"""
    model_inference_time.observe(duration) 