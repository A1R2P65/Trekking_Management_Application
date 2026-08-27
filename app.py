from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import or_ 
from models import db, User, Trek, Booking
from werkzeug.security import check_password_hash , generate_password_hash
from datetime import datetime
import os


app = Flask(__name__)
app.secret_key = 'my-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///trekking.db'

db.init_app(app)


#Admin creation with email admin@gmail.com
def create_admin():
    if not User.query.filter_by(role='admin').first():
        admin=User(name='Admin',email='admin@gmail.com',role='admin',status='Approved')
        admin.set_password('1234')
        db.session.add(admin)
        db.session.commit()
        print('Admin created,admin@gmail.com,1234')

def logged_in():
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None



@app.route('/')
def index():
    return render_template('index.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method=="POST":
        email=request.form.get('email'," ").strip()
        password=request.form.get('password'," ")
        print(email)
        print(password)
        user=User.query.filter_by(email=email).first()
        if not email or not password:
            return render_template('login.html',error='Fill all fields')
        if not user or not user.check_password(password):
            return render_template('login.html',error='Your password is wrong')
        if user.role=='trek_staff' and user.status=='Blacklisted':
            return render_template('login.html',error='You are blacklisted')
        if user.role=='trek_staff' and user.status!='Approved':
            return render_template('login.html',error='Your account is pending approval')
        if user.is_blacklisted:
            return render_template('login.html',error='You are blacklisted')
        session['user_id']=user.id
        session['role']=user.role
        session['name']=user.name
        if user.role=='admin':
            return redirect(url_for('admin_dashboard'))
        elif user.role=='trek_staff':
            return redirect(url_for('staff_dashboard'))
        else:
            return redirect(url_for('trekker_dashboard'))

    return render_template("login.html")




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method=='POST':
        role=request.form.get('role')
        print(role)
        name=request.form.get('name'," ").strip()
        print(name)
        email=request.form.get('email'," ").strip()
        print(email)
        password=request.form.get('password'," ")
        print(password)
        if not name or not email or not password or role not in ('trekker','trek_staff'):
            return render_template('index.html')
        exist=User.query.filter_by(email=email).first()
        if exist:
            return render_template("error.html")
        user=User(name=name, email=email, role=role,)
        user.set_password(password)
        print(user)

        if role=='trekker':
            user.contact=request.form.get('number')

        if role=='trek_staff':
            user.contact=request.form.get('number')

        db.session.add(user)
        db.session.commit()
        return redirect("/")
    return render_template('register.html')



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


#for stats charts
def generate_stats_chart():
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        
        treks = Trek.query.all()
        names = []
        bookings_count = []
        
        for t in treks:
            names.append(t.name)
            count = Booking.query.filter_by(trek_id=t.id).count()
            bookings_count.append(count)
            
        if not treks:
            names = ['No Treks']
            bookings_count = [0]
            
        static_dir = os.path.join(app.root_path, 'static')
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
            
        chart_path = os.path.join(static_dir, 'trek_stats.png')
        
        plt.figure(figsize=(6.5, 4))
        plt.bar(names, bookings_count, color='#198754', width=0.4)
        plt.title('Trek Popularity (Number of Bookings)', fontsize=12, fontweight='bold', color='#1f4e79')
        plt.xlabel('Trek Routes', fontsize=10)
        plt.ylabel('Bookings Count', fontsize=10)
        plt.xticks(rotation=15, ha='right', fontsize=9)
        max_val = max(bookings_count) if bookings_count else 0
        plt.yticks(range(0, max_val + 2))
        plt.tight_layout()
        plt.savefig(chart_path, dpi=100)
        plt.close()
    except Exception as e:
        print("Error generating chart:", e)

# Admin routes(Dashboard,staff approval,blacklist,trek management,user management,booking overview)

@app.route("/admin_dashboard",methods=['GET','POST'])
def admin_dashboard():
    if session.get('role') != "admin":
        return redirect(url_for('index'))

    generate_stats_chart()


    total_trekkers   = User.query.filter_by(role="trekker").count()
    total_staff      = User.query.filter_by(role="trek_staff").count()
    total_treks      = Trek.query.count()
    total_bookings   = Booking.query.count()

    pending_staff    = User.query.filter_by(role="trek_staff", status='Pending').all()
    all_trekkers     = User.query.filter_by(role="trekker").all()
    all_staff        = User.query.filter_by(role="trek_staff").all()
    all_treks        = Trek.query.all()
    all_bookings     = Booking.query.order_by(Booking.booking_date.desc()).all()

    search_query = request.args.get('q', '').strip()
    search_results_trekker = []
    search_results_staff   = []

    if search_query:
        like = f'%{search_query}%'
        search_results_trekker = User.query.filter(
            User.role == 'trekker',
            or_(User.name.like(like), User.email.like(like))
        ).all()
        search_results_staff = User.query.filter(
            User.role == 'trek_staff',
            or_(User.name.like(like), User.email.like(like))
        ).all()

    return render_template('admin_dashboard.html',
        total_trekkers=total_trekkers,
        total_staff=total_staff,
        total_treks=total_treks,
        total_bookings=total_bookings,
        pending_staff=pending_staff,
        all_trekkers=all_trekkers,
        all_staff=all_staff,
        all_treks=all_treks,
        all_bookings=all_bookings,
        search_query=search_query,
        search_results_trekker=search_results_trekker,
        search_results_staff=search_results_staff
    )



#admin_approval
@app.route('/admin/approve_staff/<int:staff_id>',methods=['GET','POST']) 
def approve_staff(staff_id):
    if session.get('role')!='admin':
        return redirect(url_for('index'))
    staff=User.query.get_or_404(staff_id)
    staff.status='Approved'
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

#admin blacklist staff
@app.route('/admin/blacklist_staff/<int:staff_id>', methods=['GET', 'POST'])
def blacklist_staff(staff_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    staff = User.query.get_or_404(staff_id)
    if staff.status == 'Blacklisted':
        staff.status = 'Approved'
    else:
        staff.status = 'Blacklisted'
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


#admin blacklist trekker
@app.route('/admin/trekkerblacklist/<int:trekker_id>', methods=['GET', 'POST'])
def blacklist_trekker(trekker_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    trekker = User.query.get_or_404(trekker_id)
    trekker.is_blacklisted = not trekker.is_blacklisted
    db.session.commit()
    return redirect(url_for('admin_dashboard'))


# Trek Management
@app.route('/admin/treks')
def admin_treks():
    return redirect(url_for('admin_dashboard'))


#add trek
@app.route('/admin/treks/add', methods=['POST'])  
def admin_add_trek():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    start = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
    end   = datetime.strptime(request.form['end_date'], '%Y-%m-%d')

    if end <= start:
        flash('End date must be after start date.', 'warning')
        return redirect(url_for('admin_dashboard'))

    trek = Trek(
        name            = request.form['name'],
        location        = request.form['location'],
        difficulty      = request.form['difficulty'],
        duration        = int(request.form['duration']),
        available_slots = int(request.form['available_slots']),
        start_date      = start,
        end_date        = end,
        status          = 'Pending'
    )
    db.session.add(trek)
    db.session.commit()
    flash('Trek created successfully.', 'success')
    return redirect(url_for('admin_dashboard'))



#edit trek
@app.route('/admin/treks/edit/<int:trek_id>', methods=['POST'])
def admin_edit_trek(trek_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    trek  = Trek.query.get_or_404(trek_id)
    start = datetime.strptime(request.form['start_date'], '%Y-%m-%d')
    end   = datetime.strptime(request.form['end_date'], '%Y-%m-%d')

    if end <= start:
        flash('End date must be after start date.', 'warning')
        return redirect(url_for('admin_dashboard'))

    trek.name            = request.form['name']
    trek.location        = request.form['location']
    trek.difficulty      = request.form['difficulty']
    trek.duration        = int(request.form['duration'])
    trek.available_slots = int(request.form['available_slots'])
    trek.status          = request.form['status']
    trek.start_date      = start
    trek.end_date        = end
    db.session.commit()
    flash('Trek updated.', 'success')
    return redirect(url_for('admin_dashboard'))


#Delete trek
@app.route('/admin/treks/delete/<int:trek_id>', methods=['POST'])
def admin_delete_trek(trek_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    trek = Trek.query.get_or_404(trek_id)
    # No need to manually delete bookings —
    # cascade='all, delete-orphan' on Trek.bookings handles it automatically
    db.session.delete(trek)
    db.session.commit()
    flash('Trek deleted.', 'info')
    return redirect(url_for('admin_dashboard'))


#Assign staff to trek
@app.route('/admin/treks/assign/<int:trek_id>', methods=['POST'])
def admin_assign_staff(trek_id):
    if session.get('role') != 'admin':
        return redirect(url_for('index'))

    trek          = Trek.query.get_or_404(trek_id)
    trek.staff_id = int(request.form['staff_id'])
    trek.status   = 'Approved'
    db.session.commit()
    flash('Staff assigned. Trek is now Approved.', 'success')
    return redirect(url_for('admin_dashboard'))


# Bookings Overview 

@app.route('/admin/bookings')
def admin_bookings():
    if session.get('role') != 'admin':
        return redirect(url_for('index'))
    return redirect(url_for('admin_dashboard'))


# Staff routes

@app.route('/staff/dashboard')
def staff_dashboard():
    if session.get('role') != 'trek_staff':
        return redirect(url_for('index'))

    staff_id = session['user_id']
    staff = User.query.get(staff_id)
    if not staff:
        session.clear()
        return redirect(url_for('login'))
    treks = Trek.query.filter_by(staff_id=staff_id).all()
    
    # Get all bookings for treks assigned to this staff member
    trek_ids = [t.id for t in treks]
    bookings = Booking.query.filter(Booking.trek_id.in_(trek_ids)).order_by(Booking.booking_date.desc()).all() if trek_ids else []

    return render_template('staff_dashboard.html', staff=staff, treks=treks, bookings=bookings)


@app.route('/staff/trek/<int:trek_id>/update', methods=['POST'])
def staff_update_trek(trek_id):
    if session.get('role') != 'trek_staff':
        return redirect(url_for('index'))

    trek = Trek.query.get_or_404(trek_id)

    # Only the assigned staff member can manage this trek
    if trek.staff_id != session['user_id']:
        flash('You are not assigned to this trek.', 'danger')
        return redirect(url_for('staff_dashboard'))

    trek.available_slots = int(request.form['available_slots'])
    trek.status          = request.form['status']
    db.session.commit()
    flash('Trek updated successfully.', 'success')
    return redirect(url_for('staff_dashboard'))


@app.route('/staff/booking/<int:booking_id>/update', methods=['POST'])
def staff_update_booking(booking_id):
    if session.get('role') != 'trek_staff':
        return redirect(url_for('index'))
    
    booking = Booking.query.get_or_404(booking_id)
    if booking.trek.staff_id != session['user_id']:
        flash('You are not authorized to manage this booking.', 'danger')
        return redirect(url_for('staff_dashboard'))
    
    new_status = request.form.get('status')
    if new_status in ('Booked', 'Cancelled', 'Completed'):
        # If transitioning to Cancelled and it was previously Booked, refund the slot
        if new_status == 'Cancelled' and booking.status == 'Booked':
            booking.trek.available_slots += 1
        # If transitioning from Cancelled to Booked, verify slots and consume one
        elif new_status == 'Booked' and booking.status == 'Cancelled':
            if booking.trek.available_slots > 0:
                booking.trek.available_slots -= 1
            else:
                flash('No slots available to reinstate booking.', 'warning')
                return redirect(url_for('staff_dashboard'))
        
        booking.status = new_status
        db.session.commit()
        flash(f'Booking status updated to {new_status}.', 'success')
    
    return redirect(url_for('staff_dashboard'))

# Trekker or user routes

@app.route('/trekker_dashboard')
def trekker_dashboard():
    if session.get('role') != 'trekker':
        return redirect(url_for('index'))

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))

    search = request.args.get('search', '')
    difficulty = request.args.get('difficulty', '')
    query = Trek.query.filter_by(status='Open')

    if search:
        query = query.filter(
            Trek.name.ilike(f'%{search}%') | Trek.location.ilike(f'%{search}%')
        )
    if difficulty:
        query = query.filter_by(difficulty=difficulty)

    open_treks = query.all()
    my_bookings = Booking.query.filter_by(user_id=user.id).all()

    return render_template('trekker_dashboard.html',
        open_treks=open_treks,
        my_bookings=my_bookings,
        user=user,
        search=search,
        difficulty=difficulty
    )


@app.route('/trekker/book/<int:trek_id>', methods=['POST'])
def trekker_book_trek(trek_id):
    if session.get('role') != 'trekker':
        return redirect(url_for('index'))

    user_id = session['user_id']
    user = User.query.get_or_404(user_id)
    if user.is_blacklisted:
        flash('You are blacklisted and cannot book treks.', 'danger')
        return redirect(url_for('trekker_dashboard'))
    trek = Trek.query.get_or_404(trek_id)

    # Rule 1: Trek must be Open
    if trek.status != 'Open':
        flash('This trek is not open for booking.', 'warning')
        return redirect(url_for('trekker_dashboard'))

    # Rule 2: Prevent overbooking
    if trek.available_slots <= 0:
        flash('No slots available.', 'warning')
        return redirect(url_for('trekker_dashboard'))

    # Rule 3: Prevent duplicate active booking
    existing = Booking.query.filter_by(
        user_id=user_id, trek_id=trek_id, status='Booked'
    ).first()
    if existing:
        flash('You have already booked this trek.', 'info')
        return redirect(url_for('trekker_dashboard'))

    booking = Booking(
        user_id      = user_id,
        trek_id      = trek_id,
        booking_date = datetime.utcnow(),
        status       = 'Booked'
    )
    trek.available_slots -= 1

    db.session.add(booking)
    db.session.commit()
    flash('Trek booked successfully!', 'success')
    return redirect(url_for('trekker_dashboard'))


@app.route('/trekker/profile', methods=['POST'])
def trekker_profile():
    if session.get('role') != 'trekker':
        return redirect(url_for('index'))

    user = User.query.get_or_404(session['user_id'])
    user.name = request.form['name']
    if request.form.get('password'):
        user.password = generate_password_hash(request.form['password'])
    db.session.commit()
    flash('Profile updated.', 'success')
    return redirect(url_for('trekker_dashboard'))




with app.app_context():
    db.create_all()
    create_admin()

if __name__ == '__main__':
    app.run(debug=True)