document.addEventListener("DOMContentLoaded", function() {
    // Modal setup
    var eventModal = new bootstrap.Modal(document.getElementById("event-modal"), {keyboard: false});
    var eventForm = document.getElementById("form-event");
    var currentEvent = null;
    var currentCalendarId = null;
    
    // Store all calendar instances
    var calendars = {};
    
    // Shared events array (optional - can be different for each calendar)
    var sharedEvents = [
        {
            title: "Sample Meeting",
            start: new Date(),
            className: "bg-primary"
        }
    ];
    
    // Calendar configurations
    var calendarConfigs = [
        {
            id: 'calendar1',
            elementId: 'calendar1',
            title: 'Today',
            dateOffset: 0  // Days from today
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
            events: [...sharedEvents], // Clone the events array
            
            // Event click handler
            eventClick: function(info) {
                currentEvent = info.event;
                currentCalendarId = config.id;
                
                document.getElementById("modal-title").innerHTML = "Edit Event";
                document.getElementById("event-title").value = currentEvent.title;
                document.getElementById("edit-event-btn").removeAttribute("hidden");
                document.getElementById("btn-save-event").setAttribute("hidden", true);
                
                eventModal.show();
            },
            
            // Date click handler for adding new events
            dateClick: function(info) {
                currentEvent = null;
                currentCalendarId = config.id;
                
                document.getElementById("modal-title").innerHTML = "Add Event to " + config.title;
                document.getElementById("event-title").value = "";
                document.getElementById("edit-event-btn").setAttribute("hidden", true);
                document.getElementById("btn-save-event").removeAttribute("hidden");
                
                eventForm.reset();
                eventModal.show();
                
                // Store the clicked date
                window.clickedInfo = {
                    date: info.date,
                    calendarId: config.id
                };
            },
            
            // Event drag handlers
            eventDrop: function(info) {
                console.log('Event moved in ' + config.title);
                // You can sync with other calendars or save to backend here
            },
            
            eventResize: function(info) {
                console.log('Event resized in ' + config.title);
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
        var category = document.getElementById("event-category").value;
        
        if (currentEvent) {
            // Update existing event
            currentEvent.setProp("title", title);
            currentEvent.setProp("classNames", [category]);
        } else if (window.clickedInfo) {
            // Add new event
            var newEvent = {
                title: title,
                start: window.clickedInfo.date,
                allDay: false,
                className: category
            };
            
            // Add to the specific calendar that was clicked
            if (calendars[window.clickedInfo.calendarId]) {
                calendars[window.clickedInfo.calendarId].addEvent(newEvent);
            }
            
            // Optional: Add to all calendars
            // Object.values(calendars).forEach(cal => cal.addEvent({...newEvent}));
            
            window.clickedInfo = null;
        }
        
        eventModal.hide();
    });
    
    // Delete event handler
    document.getElementById("btn-delete-event").addEventListener("click", function(e) {
        if (currentEvent) {
            currentEvent.remove();
            currentEvent = null;
            eventModal.hide();
        }
    });
    
    // Optional: Add a button to sync all calendars to the same date
    function createSyncButton() {
        var syncBtn = document.createElement("button");
        syncBtn.className = "btn btn-primary mb-3";
        syncBtn.textContent = "Sync All to Today";
        syncBtn.onclick = function() {
            var today = new Date();
            calendarConfigs.forEach((config, index) => {
                var targetDate = new Date(today);
                targetDate.setDate(targetDate.getDate() + index);
                calendars[config.id].gotoDate(targetDate);
            });
        };
        
        // Add button before the calendars
        var cardBody = document.querySelector(".card-body");
        if (cardBody) {
            cardBody.insertBefore(syncBtn, cardBody.firstChild);
        }
    }
    
    createSyncButton();
    
    // Optional: Function to add more calendars dynamically
    window.addNewCalendar = function(title, dateOffset) {
        var newId = 'calendar' + (Object.keys(calendars).length + 1);
        
        // Create HTML element
        var col = document.createElement('div');
        col.className = 'col-md-6 col-lg-3 mb-3';
        col.innerHTML = `
            <h5 class="mb-3">${title}</h5>
            <div id="${newId}"></div>
        `;
        
        document.querySelector('.row').appendChild(col);
        
        // Create calendar
        createCalendar({
            id: newId,
            elementId: newId,
            title: title,
            dateOffset: dateOffset
        });
    };
    
    // Example: Add a 5th calendar
    // window.addNewCalendar('In 4 Days', 4);
});