from flask import Blueprint, render_template, redirect, url_for,request, flash, current_app
from flask_login import login_required, logout_user, current_user
from models.models import ParkingLot, ParkingSpot, Booking, User
from extensions import db
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
dashboard_bp = Blueprint('dashboard', __name__)  # name MUST match 'dashboard'


#for user
@dashboard_bp.route('/user/dashboard')
@login_required
def user_dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.timestamp.desc()).all()
    lots = ParkingLot.query.options(db.joinedload(ParkingLot.spots)).all()
    return render_template('dashboard_user.html', parking_lots=lots, bookings=bookings)  # make sure this file exists!

@dashboard_bp.route('/user/book/<int:lot_id>')
@login_required
def show_booking_form(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)
    return render_template('book.html', lot=lot)

@dashboard_bp.route('/user/release')
@login_required
def show_release_form():
    return render_template('release.html')
    

@dashboard_bp.route('/user/summary')
@login_required
def user_summary():
    return render_template('summary.html')


# for admin
@dashboard_bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    lots = ParkingLot.query.options(db.joinedload(ParkingLot.spots)).all()
    # Add a new property dynamically for each lot: occupied_slots
    for lot in lots:
        lot.occupied_slots = sum(not spot.is_available for spot in lot.spots)
    
    return render_template('dashboard_admin.html', parking_lots = lots)  # make sure this file exists!

# admin users
@dashboard_bp.route('/admin/users')
@login_required
def users():
    return render_template('admin_users.html')



# admin summary
@dashboard_bp.route('/admin/summary')
@login_required
def admin_summary():
    return render_template('admin_summary.html')

@dashboard_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@dashboard_bp.route('/admin/view_spot/<int:spot_id>')
@login_required
def view_spot(spot_id):
    booking = Booking.query.filter_by(spot_id=spot_id, status='active').first()
    user = User.query.get(booking.user_id) if booking else None
    spot = ParkingSpot.query.get_or_404(spot_id)
    
    total_cost = 0
    duration_hours = 0
    no_booking = booking is None

    if booking and spot and spot.lot:
        release_time = datetime.utcnow()
        duration_hours = max(1, round((release_time - booking.timestamp).total_seconds() / 3600))
        cost_per_hour = spot.lot.price
        total_cost = duration_hours * cost_per_hour

    return render_template(
        'view_parking.html',
        spot=spot,
        booking=booking,
        user=user,
        total_cost=round(total_cost, 2),
        duration_hours=duration_hours,
        no_booking=no_booking,
        disable_delete=not no_booking  # Disable delete if there's an active booking
    )
    
    
    
    


import os
from werkzeug.utils import secure_filename




ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@dashboard_bp.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        # --- Non-sensitive fields (no password needed) ---
        current_user.full_name = request.form.get("full_name") or current_user.full_name
        current_user.address   = request.form.get("address")   or current_user.address
        current_user.pincode   = request.form.get("pincode")   or current_user.pincode

        # Handle profile image upload (optional, no password needed)
        if "profile_image" in request.files:
            file = request.files["profile_image"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                upload_folder = os.path.join(current_app.root_path, "static", "uploads")
                os.makedirs(upload_folder, exist_ok=True)
                filepath = os.path.join(upload_folder, filename)
                file.save(filepath)
                current_user.profile_image = filename

        # --- Sensitive changes (require old password) ---
        new_email     = request.form.get("email")
        old_password  = request.form.get("old_password") or ""
        new_password  = (request.form.get("new_password") or "").strip()

        email_changed    = bool(new_email) and (new_email != current_user.email)
        password_changed = bool(new_password)

        if email_changed or password_changed:
            # Must supply the correct current password to proceed
            if not old_password:
                flash("Enter your old password to change email or set a new password.", "warning")
                return redirect(url_for("dashboard.edit_profile"))

            if not check_password_hash(current_user.password, old_password):
                flash("Old password is incorrect. Email/password not updated.", "danger")
                return redirect(url_for("dashboard.edit_profile"))

            # Apply sensitive changes
            if email_changed:
                current_user.email = new_email
            if password_changed:
                current_user.password = generate_password_hash(new_password)

        db.session.commit()
        flash("Profile updated successfully!", "success")

        # Redirect based on role
        return redirect(url_for("dashboard.user_dashboard" if getattr(current_user, "role", "user") == "user"
                                else "dashboard.admin_dashboard"))

    return render_template("edit_profile.html")


@dashboard_bp.route("/remove-profile-image", methods=["POST"])
@login_required
def remove_profile_image():
    # reset to default
    current_user.profile_image = "default_profile.jpg"
    db.session.commit()
    flash("Profile image removed.", "info")
    return redirect(url_for("dashboard.edit_profile"))