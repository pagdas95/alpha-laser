/**
 * Room-Based Calendar - Updated for your Appointment model
 * Copy to: static/assets/js/pages/calendar_rooms.init.js
 */
document.addEventListener("DOMContentLoaded", function() {
    // Get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');
    
    // Modal setup
    var eventModal = new bootstrap.Modal(document.getElementById("event-modal"), {keyboard: false});
    var currentEvent = null;
    
    // Store all calendar instances
    var calendars = {};
    var currentDate = new Date();
    
    // Get rooms data from template
    var roomsData = [];
    document.querySelectorAll('[data-room-id]').forEach(function(el) {
        roomsData.push({
            id: el.dataset.roomId,
            name: el.dataset.roomName,
            elementId: el.id
        });
    });
    
    // Create calendar for each room
    function createRoomCalendar(roomConfig) {
        var calendarEl = document.getElementById(roomConfig.elementId);
        if (!calendarEl) return;
        
        var calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'timeGridDay',
            headerToolbar: {
                left: '',
                center: '',
                right: ''
            },
            initialDate: currentDate,
            editable: true,
            droppable: true,
            selectable: true,
            navLinks: false,
            height: 500,
            slotMinTime: '07:00:00',
            slotMaxTime: '22:00:00',
            slotDuration: '00:30:00',
            
            // Fetch events from Django filtered by room
            events: function(info, successCallback, failureCallback) {
                fetch('/appointments/api/room-appointments/?start=' + info.startStr + 
                      '&end=' + info.endStr + 
                      '&room_id=' + roomConfig.id)
                    .then(response => response.json())
                    .then(data => {
                        successCallback(data);
                    })
                    .catch(error => {
                        console.error('Error fetching appointments for ' + roomConfig.name + ':', error);
                        failureCallback(error);
                    });
            },
            
            // Event click handler
            eventClick: function(info) {
                currentEvent = info.event;
                
                // Populate modal
                document.getElementById("modal-title").innerHTML = "Λεπτομέρειες Ραντεβού";
                document.getElementById("event-title").value = currentEvent.title;
                
                // Get extended props
                var props = currentEvent.extendedProps;
                
                // Format times
                var startTime = new Date(currentEvent.start);
                var endTime = new Date(currentEvent.end);
                var timeFormat = { hour: '2-digit', minute: '2-digit' };
                
                // Build details HTML
                var detailsHtml = `
                    <div class="row">
                        <div class="col-md-6">
                            <p class="mb-2"><strong>Πελάτης:</strong> ${props.clientName}</p>
                            <p class="mb-2"><strong>Υπηρεσία:</strong> ${props.serviceName}</p>
                            <p class="mb-2"><strong>Δωμάτιο:</strong> ${props.roomName}</p>
                        </div>
                        <div class="col-md-6">
                            <p class="mb-2"><strong>Προσωπικό:</strong> ${props.staffName}</p>
                            ${props.machineName ? '<p class="mb-2"><strong>Μηχάνημα:</strong> ' + props.machineName + '</p>' : ''}
                            <p class="mb-2"><strong>Κατάσταση:</strong> <span class="badge ${currentEvent.classNames[0]}">${props.statusDisplay}</span></p>
                        </div>
                    </div>
                    <hr>
                    <div class="row">
                        <div class="col-12">
                            <p class="mb-2"><strong>Ώρα:</strong> ${startTime.toLocaleTimeString('el-GR', timeFormat)} - ${endTime.toLocaleTimeString('el-GR', timeFormat)}</p>
                            ${props.notes ? '<p class="mb-0"><strong>Σημειώσεις:</strong> ' + props.notes + '</p>' : ''}
                        </div>
                    </div>
                `;
                
                var detailsContainer = document.getElementById("appointment-details");
                if (detailsContainer) {
                    detailsContainer.innerHTML = detailsHtml;
                }
                
                // Store appointment ID
                document.getElementById("eventid").value = currentEvent.id;
                
                eventModal.show();
            },
            
            // Date click - redirect to create form
            dateClick: function(info) {
                var clickedDateTime = info.date.toISOString();
                window.location.href = `/appointments/create/?room=${roomConfig.id}&start=${clickedDateTime}`;
            },
            
            // Event drag - update appointment
            eventDrop: function(info) {
                var appointmentId = info.event.id;
                var newStart = info.event.start.toISOString();
                
                fetch(`/appointments/api/appointments/${appointmentId}/update/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify({
                        start: newStart,
                        room_id: roomConfig.id
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('Appointment moved successfully');
                        // Refresh all calendars
                        Object.values(calendars).forEach(cal => cal.refetchEvents());
                    } else {
                        alert('Σφάλμα: ' + data.message);
                        info.revert();
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Σφάλμα κατά την ενημέρωση');
                    info.revert();
                });
            },
            
            // Event resize - update duration
            eventResize: function(info) {
                var appointmentId = info.event.id;
                var newStart = info.event.start.toISOString();
                var newEnd = info.event.end ? info.event.end.toISOString() : null;
                
                fetch(`/appointments/api/appointments/${appointmentId}/update/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify({
                        start: newStart,
                        end: newEnd
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (!data.success) {
                        alert('Σφάλμα: ' + data.message);
                        info.revert();
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Σφάλμα κατά την ενημέρωση');
                    info.revert();
                });
            }
        });
        
        calendars[roomConfig.id] = calendar;
        calendar.render();
        
        return calendar;
    }
    
    // Initialize all room calendars
    roomsData.forEach(roomConfig => {
        createRoomCalendar(roomConfig);
    });
    
    // Navigation controls
    document.getElementById('prev-day')?.addEventListener('click', function() {
        currentDate.setDate(currentDate.getDate() - 1);
        Object.values(calendars).forEach(cal => {
            cal.gotoDate(currentDate);
        });
        updateDateDisplay();
    });
    
    document.getElementById('next-day')?.addEventListener('click', function() {
        currentDate.setDate(currentDate.getDate() + 1);
        Object.values(calendars).forEach(cal => {
            cal.gotoDate(currentDate);
        });
        updateDateDisplay();
    });
    
    document.getElementById('today-btn')?.addEventListener('click', function() {
        currentDate = new Date();
        Object.values(calendars).forEach(cal => {
            cal.gotoDate(currentDate);
        });
        updateDateDisplay();
    });
    
    // Update date display
    function updateDateDisplay() {
        var dateDisplay = document.getElementById('current-date-display');
        if (dateDisplay) {
            var options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            dateDisplay.textContent = currentDate.toLocaleDateString('el-GR', options);
        }
    }
    
    // Initial date display
    updateDateDisplay();
    
    // Refresh all calendars
    document.getElementById('refresh-all')?.addEventListener('click', function() {
        Object.values(calendars).forEach(cal => cal.refetchEvents());
    });
    
    // Delete appointment
    document.getElementById("btn-delete-event")?.addEventListener("click", function(e) {
        if (currentEvent && confirm('Είστε σίγουροι ότι θέλετε να διαγράψετε αυτό το ραντεβού;')) {
            var appointmentId = currentEvent.id;
            
            fetch(`/appointments/api/appointments/${appointmentId}/delete/`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    Object.values(calendars).forEach(cal => cal.refetchEvents());
                    eventModal.hide();
                    alert('Το ραντεβού διαγράφηκε επιτυχώς!');
                } else {
                    alert('Σφάλμα: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Σφάλμα κατά τη διαγραφή');
            });
        }
    });
    
    // Auto-refresh every 5 minutes
    setInterval(function() {
        Object.values(calendars).forEach(cal => cal.refetchEvents());
    }, 300000);
});