/**
 * Calendar Integration with Django Appointments
 * Updated version of calendar2.init.js
 */
document.addEventListener("DOMContentLoaded", function() {
    // Get CSRF token for Django
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
    var eventForm = document.getElementById("form-event");
    var currentEvent = null;
    var currentCalendarId = null;
    
    // Store all calendar instances
    var calendars = {};
    
    // Calendar configurations
    var calendarConfigs = [
        {
            id: 'calendar1',
            elementId: 'calendar1',
            title: 'Today',
            dateOffset: 0
        },
        {
            id: 'calendar2',
            elementId: 'calendar2',
            title: 'Tomorrow',
            dateOffset: 1
        },
        {
            id: 'calendar3',
            elementId: 'calendar3',
            title: 'Day After Tomorrow',
            dateOffset: 2
        },
        {
            id: 'calendar4',
            elementId: 'calendar4',
            title: 'In 3 Days',
            dateOffset: 3
        }
    ];
    
    // Function to create a calendar
    function createCalendar(config) {
        var calendarEl = document.getElementById(config.elementId);
        if (!calendarEl) return;
        
        // Calculate the date for this calendar
        var calendarDate = new Date();
        calendarDate.setDate(calendarDate.getDate() + config.dateOffset);
        
        var calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'timeGridDay',
            headerToolbar: {
                left: 'prev',
                center: 'title',
                right: 'next'
            },
            initialDate: calendarDate,
            editable: true,
            droppable: true,
            selectable: true,
            navLinks: false,
            height: 500,
            slotMinTime: '07:00:00',
            slotMaxTime: '22:00:00',
            slotDuration: '00:30:00',
            
            // Fetch events from Django
            events: function(info, successCallback, failureCallback) {
                fetch('/appointments/api/appointments/?start=' + info.startStr + '&end=' + info.endStr)
                    .then(response => response.json())
                    .then(data => {
                        successCallback(data);
                    })
                    .catch(error => {
                        console.error('Error fetching appointments:', error);
                        failureCallback(error);
                    });
            },
            
            // Event click handler
            eventClick: function(info) {
                currentEvent = info.event;
                currentCalendarId = config.id;
                
                // Populate modal with event data
                document.getElementById("modal-title").innerHTML = "Edit Appointment";
                document.getElementById("event-title").value = currentEvent.title;
                
                // Get extended props
                var props = currentEvent.extendedProps;
                document.getElementById("event-notes").value = props.notes || '';
                
                // Show/hide appropriate buttons
                document.getElementById("edit-event-btn").removeAttribute("hidden");
                document.getElementById("btn-save-event").setAttribute("hidden", true);
                document.getElementById("btn-delete-event").removeAttribute("hidden");
                
                // Store appointment ID
                document.getElementById("eventid").value = currentEvent.id;
                
                eventModal.show();
            },
            
            // Date click handler for adding new appointments
            dateClick: function(info) {
                currentEvent = null;
                currentCalendarId = config.id;
                
                document.getElementById("modal-title").innerHTML = "Add Appointment - " + config.title;
                document.getElementById("event-title").value = "";
                document.getElementById("event-notes").value = "";
                document.getElementById("edit-event-btn").setAttribute("hidden", true);
                document.getElementById("btn-save-event").removeAttribute("hidden");
                document.getElementById("btn-delete-event").setAttribute("hidden", true);
                
                eventForm.reset();
                eventModal.show();
                
                // Store the clicked date
                window.clickedInfo = {
                    date: info.date,
                    calendarId: config.id
                };
            },
            
            // Event drag handler - Update appointment time
            eventDrop: function(info) {
                var appointmentId = info.event.id;
                var newStart = info.event.start.toISOString();
                
                // Update via AJAX
                fetch(`/appointments/api/appointments/${appointmentId}/update/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify({
                        start: newStart
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        console.log('Appointment moved successfully');
                        // Refresh all calendars
                        Object.values(calendars).forEach(cal => cal.refetchEvents());
                    } else {
                        alert('Error updating appointment: ' + data.message);
                        info.revert();
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error updating appointment');
                    info.revert();
                });
            },
            
            // Event resize handler - Update appointment duration
            eventResize: function(info) {
                var appointmentId = info.event.id;
                var newStart = info.event.start.toISOString();
                var newEnd = info.event.end ? info.event.end.toISOString() : null;
                
                // Update via AJAX
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
                    if (data.success) {
                        console.log('Appointment duration updated');
                    } else {
                        alert('Error updating appointment: ' + data.message);
                        info.revert();
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('Error updating appointment');
                    info.revert();
                });
            }
        });
        
        // Store the calendar instance
        calendars[config.id] = calendar;
        
        // Render the calendar
        calendar.render();
        
        return calendar;
    }
    
    // Initialize all calendars
    calendarConfigs.forEach(config => {
        createCalendar(config);
    });
    
    // Form submission handler
    eventForm.addEventListener("submit", function(e) {
        e.preventDefault();
        
        var title = document.getElementById("event-title").value;
        var notes = document.getElementById("event-notes").value;
        var appointmentId = document.getElementById("eventid").value;
        
        if (currentEvent && appointmentId) {
            // Update existing appointment
            fetch(`/appointments/api/appointments/${appointmentId}/update/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({
                    notes: notes
                    // Add other fields as needed
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Refresh all calendars
                    Object.values(calendars).forEach(cal => cal.refetchEvents());
                    eventModal.hide();
                    alert('Appointment updated successfully!');
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error updating appointment');
            });
            
        } else if (window.clickedInfo) {
            // Create new appointment
            // Note: You'll need to get client and service from a form
            // This is a simplified version
            alert('To create appointments, please use the full appointment creation form.');
            // Or redirect to your create appointment page:
            // window.location.href = '/appointments/create/?date=' + window.clickedInfo.date.toISOString();
            
            eventModal.hide();
        }
    });
    
    // Delete appointment handler
    document.getElementById("btn-delete-event").addEventListener("click", function(e) {
        if (currentEvent && confirm('Are you sure you want to delete this appointment?')) {
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
                    // Refresh all calendars
                    Object.values(calendars).forEach(cal => cal.refetchEvents());
                    eventModal.hide();
                    alert('Appointment deleted successfully!');
                } else {
                    alert('Error: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Error deleting appointment');
            });
        }
    });
    
    // Sync all calendars to consecutive days starting from today
    function createSyncButton() {
        var syncBtn = document.createElement("button");
        syncBtn.className = "btn btn-primary mb-3 me-2";
        syncBtn.textContent = "Sync to Today";
        syncBtn.onclick = function() {
            var today = new Date();
            calendarConfigs.forEach((config, index) => {
                var targetDate = new Date(today);
                targetDate.setDate(targetDate.getDate() + index);
                calendars[config.id].gotoDate(targetDate);
            });
        };
        
        var refreshBtn = document.createElement("button");
        refreshBtn.className = "btn btn-success mb-3";
        refreshBtn.textContent = "Refresh All";
        refreshBtn.onclick = function() {
            Object.values(calendars).forEach(cal => cal.refetchEvents());
        };
        
        // Add buttons before the calendars
        var cardBody = document.querySelector(".card-body");
        if (cardBody) {
            var buttonContainer = document.createElement("div");
            buttonContainer.appendChild(syncBtn);
            buttonContainer.appendChild(refreshBtn);
            cardBody.insertBefore(buttonContainer, cardBody.firstChild);
        }
    }
    
    createSyncButton();
    
    // Auto-refresh every 5 minutes
    setInterval(function() {
        Object.values(calendars).forEach(cal => cal.refetchEvents());
    }, 300000); // 5 minutes
});