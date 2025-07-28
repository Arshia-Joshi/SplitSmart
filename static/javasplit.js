document.addEventListener('DOMContentLoaded', function() {
    const peopleCountInput = document.getElementById('peopleCount'); // Renamed for clarity
    const peopleContainer = document.getElementById('peopleContainer');
    const itemsList = document.getElementById('itemsList');

    // Initial setup when the page loads
    updatePeopleInputs(); 
    
    // Event listener for changes in the number of people
    peopleCountInput.addEventListener('change', updatePeopleInputs);
    
    // Event listener for item checkboxes (to show/hide person checkboxes)
    itemsList.addEventListener('change', function(e) {
        if (e.target.classList.contains('item-checkbox')) {
            const itemContainer = e.target.closest('.item-container');
            const checkboxesContainer = itemContainer.querySelector('.people-checkboxes');
            checkboxesContainer.style.display = e.target.checked ? 'block' : 'none';

            // If the main item checkbox is unchecked, uncheck all associated person checkboxes
            if (!e.target.checked) {
                checkboxesContainer.querySelectorAll('.person-item-checkbox').forEach(checkbox => {
                    checkbox.checked = false;
                });
            }
        }
        // Recalculate totals whenever a person's item checkbox changes
        updateIndividualTotals(); 
    });

    // Event listener for person-item checkboxes to update individual totals
    peopleContainer.addEventListener('change', updateIndividualTotals); // Listen for changes within peopleContainer
    itemsList.addEventListener('change', function(e) {
        if (e.target.classList.contains('person-item-checkbox')) { // Only react to person-item-checkbox changes
            updateIndividualTotals();
        }
    });

    function updatePeopleInputs() {
        const count = parseInt(peopleCountInput.value);
        peopleContainer.innerHTML = ''; // Clear previous inputs

        for (let i = 1; i <= count; i++) {
            const personDiv = document.createElement('div');
            personDiv.className = 'person-card mb-3'; // Added mb-3 for spacing
            personDiv.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <h5><i class="fas fa-user me-2"></i> Person ${i}</h5>
                    <span class="person-total fw-bold"></span> </div>
                <input type="text" class="form-control mb-2" 
                        placeholder="Name (optional)" name="person_${i}_name" id="person_${i}_name">
                <div class="person-items" data-person-id="${i}">
                    </div>
            `;
            peopleContainer.appendChild(personDiv);
        }
        
        // After updating people inputs, regenerate item checkboxes for people
        updateItemCheckboxes(count);
        updateIndividualTotals(); // Update totals immediately after refreshing inputs
    }
    
    function updateItemCheckboxes(personCount) {
        // Iterate through each main item container on the page
        document.querySelectorAll('.item-container').forEach((itemContainer) => {
            const checkboxesContainer = itemContainer.querySelector('.people-checkboxes');
            checkboxesContainer.innerHTML = ''; // Clear existing person checkboxes for this item

            // Get the item's unique index from the data attribute
            const itemIndex = itemContainer.dataset.itemIndex; 
            const itemPrice = parseFloat(itemContainer.querySelector(`input[name="item_${itemIndex}_price"]`).value);

            for (let i = 1; i <= personCount; i++) {
                const checkboxDiv = document.createElement('div');
                checkboxDiv.className = 'form-check form-check-inline';
                checkboxDiv.innerHTML = `
                    <input class="form-check-input person-item-checkbox" type="checkbox" 
                           name="person_${i}_item_${itemIndex}" value="on" 
                           data-person-id="${i}" data-item-price="${itemPrice}" data-item-index="${itemIndex}">
                    <label class="form-check-label" for="person_${i}_item_${itemIndex}">Person ${i}</label>
                `;
                checkboxesContainer.appendChild(checkboxDiv);
            }
        });
    }

    
    function updateIndividualTotals() {
        const peopleTotals = {};
        const peopleCount = parseInt(peopleCountInput.value);

    
        for (let i = 1; i <= peopleCount; i++) {
            peopleTotals[i] = 0;
        }

        
        document.querySelectorAll('.person-item-checkbox:checked').forEach(checkbox => {
            const personId = parseInt(checkbox.dataset.personId);
            const itemPrice = parseFloat(checkbox.dataset.itemPrice);
            if (!isNaN(itemPrice)) {
                peopleTotals[personId] += itemPrice;
            }
        });

        
        for (let i = 1; i <= peopleCount; i++) {
            const personCard = peopleContainer.querySelector(`.person-card:nth-child(${i})`);
            if (personCard) {
                const totalSpan = personCard.querySelector('.person-total');
                if (totalSpan) {
                    totalSpan.textContent = `$${peopleTotals[i].toFixed(2)}`;
                }
            }
        }
    }
});