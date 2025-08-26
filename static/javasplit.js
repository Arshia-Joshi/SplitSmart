document.addEventListener('DOMContentLoaded', function() {
    const peopleCountInput = document.getElementById('peopleCount');
    const peopleContainer = document.getElementById('peopleContainer');
    const itemsList = document.getElementById('itemsList');

    // Initial setup
    updatePeopleInputs();

    // Update when number of people changes
    peopleCountInput.addEventListener('change', updatePeopleInputs);

    // Toggle people checkboxes when item is checked
    itemsList.addEventListener('change', function(e) {
        if (e.target.classList.contains('item-checkbox')) {
            const itemContainer = e.target.closest('.item-container');
            const checkboxesContainer = itemContainer.querySelector('.people-checkboxes');
            checkboxesContainer.style.display = e.target.checked ? 'block' : 'none';

            // If unchecked, reset sub-checkboxes
            if (!e.target.checked) {
                checkboxesContainer.querySelectorAll('.person-item-checkbox').forEach(cb => cb.checked = false);
            }
        }
        updateIndividualTotals();
    });

    // Update totals whenever a person-item checkbox changes
    itemsList.addEventListener('change', function(e) {
        if (e.target.classList.contains('person-item-checkbox')) {
            updateIndividualTotals();
        }
    });

    function updatePeopleInputs() {
        const count = parseInt(peopleCountInput.value);
        peopleContainer.innerHTML = '';

        for (let i = 1; i <= count; i++) {
            const personDiv = document.createElement('div');
            personDiv.className = 'person-card mb-3';
            personDiv.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <h5><i class="fas fa-user me-2"></i> Person ${i}</h5>
                    <span class="person-total fw-bold"></span>
                </div>
                <input type="text" class="form-control mb-2" 
                       placeholder="Name (optional)" name="person_${i}_name" id="person_${i}_name">
                <div class="person-items" data-person-id="${i}"></div>
            `;
            peopleContainer.appendChild(personDiv);
        }

        // Regenerate item checkboxes
        updateItemCheckboxes(count);
        updateIndividualTotals();
    }

    function updateItemCheckboxes(personCount) {
        document.querySelectorAll('.item-container').forEach((itemContainer) => {
            const checkboxesContainer = itemContainer.querySelector('.people-checkboxes');
            checkboxesContainer.innerHTML = '';

            const itemIndex = itemContainer.dataset.itemIndex;
            const priceInput = itemContainer.querySelector(`input[name="item_${itemIndex}_price"]`);
            const itemPrice = parseFloat(priceInput.value);

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

        document.querySelectorAll('.person-item-checkbox:checked').forEach(cb => {
            const personId = parseInt(cb.dataset.personId);
            const itemPrice = parseFloat(cb.dataset.itemPrice);
            if (!isNaN(itemPrice)) {
                peopleTotals[personId] += itemPrice;
            }
        });

        for (let i = 1; i <= peopleCount; i++) {
            const personCard = peopleContainer.querySelector(`.person-card:nth-child(${i})`);
            if (personCard) {
                const totalSpan = personCard.querySelector('.person-total');
                if (totalSpan) {
                    totalSpan.textContent = `Rs ${peopleTotals[i].toFixed(2)}`;
                }
            }
        }
    }
});
