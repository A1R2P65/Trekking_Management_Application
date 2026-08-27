import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash,generate_password_hash

db = SQLAlchemy()


class User(db.Model):

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password      = db.Column(db.String(200), nullable=False)
    contact       = db.Column(db.String(20))#NEW
    is_blacklisted = db.Column(db.Boolean, default=False)
    role=db.Column(db.String(20), nullable=False) # Admin,Trek_staff,Trekker
    status = db.Column(db.String(20), default='Pending')  # Pending/Approved/Rejected
 

    def set_password(self,raw): #self refers to the specific instance (or object) of the class that is currently being used.
        #It takes the raw (plain text) password that the user typed in, passes it through a function called generate_password_hash(), and saves the resulting scrambled string into the database column self.password
        self.password=generate_password_hash(raw)
    def check_password(self,raw):
        return check_password_hash(self.password, raw)


#TREK 
#One Trek → Many Bookings (One --> Many relationship)
class Trek(db.Model):

    id              = db.Column(db.Integer, primary_key=True)
    name            = db.Column(db.String(150), nullable=False)
    location        = db.Column(db.String(150), nullable=False)
    difficulty      = db.Column(db.String(20), nullable=False)  # Easy/Moderate/Hard
    duration        = db.Column(db.Integer, nullable=False)     # in days
    available_slots = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    created_at=db.Column(db.DateTime,default=datetime.datetime.now)

    # Pending → Approved → Open → Closed → Completed

    start_date      = db.Column(db.Date)
    end_date        = db.Column(db.Date)

    # FK: which staff is assigned to this trek
    staff_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    staff = db.relationship('User', foreign_keys=[staff_id], backref='assigned_treks')

    # One trek → many bookings
    bookings = db.relationship('Booking', backref='trek', lazy=True, cascade='all, delete-orphan')


# BOOKING 
class Booking(db.Model):

    id           = db.Column(db.Integer, primary_key=True)
    booking_date = db.Column(db.DateTime, nullable=False)
    status       = db.Column(db.String(20), default='Booked')
    # Booked / Cancelled / Completed

    # FK: which user made this booking
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # FK: which trek is being booked
    trek_id = db.Column(db.Integer, db.ForeignKey('trek.id'), nullable=False)

    # One user makes many bookings; each booking belongs to one user
    user = db.relationship('User', foreign_keys=[user_id], backref='bookings')
    