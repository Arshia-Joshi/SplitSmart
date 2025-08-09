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
        personDiv.className = 'person-card mb-3';
        personDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <h5><i class="fas fa-user me-2"></i> Person ${i}</h5>
                <span class="person-total fw-bold"></span>
            </div>
            <input type="text" class="form-control mb-2"
                   placeholder="Name (optional)" 
                   name="person_${i}_name" id="person_${i}_name">

            <input type="tel" class="form-control mb-2"
                   placeholder="WhatsApp Number (+1234567890)" 
                   name="person_${i}_phone" id="person_${i}_phone">

            <div class="person-items" data-person-id="${i}"></div>
        `;
        peopleContainer.appendChild(personDiv);
    }

    // After updating people inputs, regenerate item checkboxes for people
    updateItemCheckboxes(count);
    updateIndividualTotals(); // Update totals immediately
}

    function updateItemCheckboxes(personCount) {
        // Iterate through each main item container on the page
        document.querySelectorAll('.item-container').forEach((itemContainer) => {
            const checkboxesContainer = itemContainer.querySelector('.people-checkboxes');
            checkboxesContainer.innerHTML = ''; // Clear existing person checkboxes for this item

            // Get the item's unique index from the data attribute
            const itemIndex = itemContainer.dataset.itemIndex; 
            const itemPrice = parseFloat(itemContainer.querySelector(`input[name="item_Rs{itemIndex}_price"]`).value);

            for (let i = 1; i <= personCount; i++) {
                const checkboxDiv = document.createElement('div');
                checkboxDiv.className = 'form-check form-check-inline';
                checkboxDiv.innerHTML = `
                    <input class="form-check-input person-item-checkbox" type="checkbox" 
                           name="person_Rs{i}_item_Rs{itemIndex}" value="on" 
                           data-person-id="Rs{i}" data-item-price="Rs{itemPrice}" data-item-index="Rs{itemIndex}">
                    <label class="form-check-label" for="person_Rs{i}_item_Rs{itemIndex}">Person Rs{i}</label>
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

        document.getElementById('submitBtn').addEventListener('click', async () => {
    const people = [];
    const peopleCount = parseInt(document.getElementById('peopleCount').value);

    for (let i = 1; i <= peopleCount; i++) {
        const name = document.getElementById(`person_${i}_name`).value.trim() || `Person ${i}`;
        const phone = document.getElementById(`person_${i}_phone`).value.trim();
        people.push({ name, phone });
    }

    const imageFile = document.getElementById('billImage').files[0];
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('people', JSON.stringify(people));

    try {
        const response = await fetch('/split_bill', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();
        console.log('API Response:', result);
    } catch (error) {
        console.error('Error sending data to Flask:', error);
    }
});

        for (let i = 1; i <= peopleCount; i++) {
            const personCard = peopleContainer.querySelector(`.person-card:nth-child(Rs{i})`);
            if (personCard) {
                const totalSpan = personCard.querySelector('.person-total');
                if (totalSpan) {
                    totalSpan.textContent = `RsRs{peopleTotals[i].toFixed(2)}`;
                }
            }
        }
    }
});