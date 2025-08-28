from flask import Blueprint, redirect, url_for, flash, request, render_template
from flask_login import login_required, current_user
from models.models import db, ParkingSpot, Booking, ParkingLot
from datetime import datetime


user_bp = Blueprint('user', __name__)





@user_bp.route('/book/<int:lot_id>', methods=['GET', 'POST'])
@login_required
def book_parking_lot(lot_id):
    lot = ParkingLot.query.get_or_404(lot_id)

    # ✅ Get the first available spot in the lot
    available_spot = ParkingSpot.query.filter_by(lot_id=lot.id, is_available=True).order_by(ParkingSpot.spot_number).first()

    if not available_spot:
        flash('No available slots in this parking lot.', 'danger')
        return redirect(url_for('user.search_results'))

    if request.method == 'POST':
        vehicle_no = request.form['vehicle_number']

        # ✅ Create booking
        booking = Booking(
            user_id=current_user.id,
            lot_id=lot.id,
            vehicle_no=vehicle_no,
            spot_id=available_spot.id,
        )

        # ✅ Mark spot as booked
        available_spot.is_available = False
        db.session.add(booking)
        db.session.commit()

        flash(f'Parking spot {available_spot.spot_number} booked successfully!', 'success')
        return redirect(url_for('dashboard.user_dashboard'))

    return render_template('book.html', lot=lot, spot=available_spot)


@user_bp.route('/user/release/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def release_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id:
        flash('Unauthorized action!', 'danger')
        return redirect(url_for('dashboard.user_dashboard'))

    spot = ParkingSpot.query.get(booking.spot_id)
    if not spot:
        flash('Parking spot not found.', "danger")
        return redirect(url_for('dashboard.user_dashboard'))

    # GET request - show confirmation page
    if request.method == 'GET':
        release_time = datetime.utcnow()
        duration_hours = max(1, round((release_time - booking.timestamp).total_seconds() / 3600))
        total_cost = duration_hours * spot.lot.price

        return render_template(
            'release.html',
            booking=booking,
            spot=spot,
            release_time=datetime.utcnow(),
            duration_hours=duration_hours,
            total_cost=round(total_cost, 2)
        )

    # POST request — finalize release
    if booking.status != 'active':
        flash('This booking is already released.', 'info')
        return redirect(url_for('dashboard.user_dashboard'))

    # Calculate cost again
    release_time = datetime.utcnow()
    duration_hours = (release_time - booking.timestamp).total_seconds() / 3600
    duration_hours = max(1, round(duration_hours))
    cost_per_hour = spot.lot.price
    total_cost = duration_hours * cost_per_hour

    # Update booking
    booking.status = 'released'
    booking.release_time = release_time
    booking.cost = total_cost

    # Update spot availability
    spot.is_available = True
    spot.lot.available_slots +=1

    db.session.commit()

    flash(f'Booking released! Duration: {duration_hours} hour(s), Cost: ₹{total_cost:.2f}', 'success')
    return redirect(url_for('dashboard.user_dashboard'))

   