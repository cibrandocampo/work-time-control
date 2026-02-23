(function() {
    'use strict';

    function getCSRFToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }

    function fetchLocationHours(locationId) {
        if (!locationId) return;

        fetch(`/admin/workdays/workday/get-location-hours/${locationId}/`, {
            headers: {
                'X-CSRFToken': getCSRFToken(),
            }
        })
        .then(response => response.json())
        .then(data => {
            const expectedHoursField = document.getElementById('id_expected_hours');
            if (expectedHoursField && !expectedHoursField.value) {
                expectedHoursField.value = data.hours;
            }
        })
        .catch(error => console.error('Error fetching location hours:', error));
    }

    function initLocationListener() {
        // For autocomplete fields, we need to watch for changes in the hidden input
        const locationField = document.getElementById('id_location');
        if (!locationField) return;

        // Create a MutationObserver to watch for value changes
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'attributes' && mutation.attributeName === 'value') {
                    const locationId = locationField.value;
                    if (locationId) {
                        fetchLocationHours(locationId);
                    }
                }
            });
        });

        observer.observe(locationField, { attributes: true });

        // Also listen for change events (for select2/autocomplete)
        locationField.addEventListener('change', function() {
            const locationId = this.value;
            if (locationId) {
                fetchLocationHours(locationId);
            }
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initLocationListener);
    } else {
        initLocationListener();
    }
})();
