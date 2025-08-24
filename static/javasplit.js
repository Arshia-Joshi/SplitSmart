document.addEventListener('DOMContentLoaded', function() {
    const peopleCountInput = document.getElementById('peopleCount');
    const peopleContainer = document.getElementById('peopleContainer');
    const itemsList = document.getElementById('itemsList');
    const submitBtn = document.getElementById('submitBtn');

    // This is the new part for handling manual edits
    itemsList.addEventListener('input', function(e) {
        if (e.target.classList.contains('item-price-input')) {
            updateIndividualTotals();
        }
    });

    // Initial setup
    updatePeopleInputs(); 
    
    // Event listeners for UI changes
    peopleCountInput.addEventListener('change', updatePeopleInputs);
    
    itemsList.addEventListener('change', function(e) {
        if (e.target.classList.contains('item-checkbox')) {
            const itemContainer = e.target.closest('.item-container');
            const checkboxesContainer = itemContainer.querySelector('.people-checkboxes');
            checkboxesContainer.style.display = e.target.checked ? 'block' : 'none';

            if (!e.target.checked) {
                checkboxesContainer.querySelectorAll('.person-item-checkbox').forEach(checkbox => {
                    checkbox.checked = false;
                });
            }
        }
        updateIndividualTotals(); 
    });

    peopleContainer.addEventListener('change', updateIndividualTotals);
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
                    <span class="person-total fw-bold">$0.00</span>
                </div>
                <input type="text" class="form-control mb-2" 
                       placeholder="Name (optional)" 
                       name="person_${i}_name" 
                       id="person_${i}_name">
                <input type="tel" class="form-control mb-2" 
                       placeholder="Number (10 digits)" 
                       name="number_${i}_number" 
                       id="person_${i}_number"
                       pattern="[0-9]{10}" 
                       maxlength="10" 
                       oninput="this.value = this.value.replace(/[^0-9]/g, '')">
                <div class="person-items" data-person-id="${i}">
                </div>
            `;
            peopleContainer.appendChild(personDiv);
        }
        
        updateItemCheckboxes(count);
        updateIndividualTotals();
    }

    function updateItemCheckboxes(personCount) {
        document.querySelectorAll('.item-container').forEach((itemContainer) => {
            const checkboxesContainer = itemContainer.querySelector('.people-checkboxes');
            checkboxesContainer.innerHTML = ''; 

            const itemIndex = itemContainer.dataset.itemIndex;
            
            for (let i = 1; i <= personCount; i++) {
                const checkboxDiv = document.createElement('div');
                checkboxDiv.className = 'form-check form-check-inline';
                checkboxDiv.innerHTML = `
                    <input class="form-check-input person-item-checkbox" type="checkbox" 
                           name="person_${i}_item_${itemIndex}" 
                           value="on" 
                           data-person-id="${i}" 
                           data-item-index="${itemIndex}">
                    <label class="form-check-label" for="person_${i}_item_${itemIndex}">Person ${i}</label>
                `;
                checkboxesContainer.appendChild(checkboxDiv);
            }
        });
    }
document.getElementById("splitForm").addEventListener("submit", function(e) {
    e.preventDefault(); // stop normal form submit

    let peopleCount = document.getElementById("peopleCount").value;
    let items = [];
    document.querySelectorAll(".item-container").forEach((el, idx) => {
        let name = el.querySelector("input[name='item_" + idx + "_name']").value;
        let price = parseFloat(el.querySelector("input[name='item_" + idx + "_price']").value);
        items.push({ name, price });
    });

    let payload = {
        peopleCount: parseInt(peopleCount),
        people: [], // you’ll need to build this from your form
        items: items,
        personItems: {} // also build this mapping
    };

    fetch("/calculate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => console.log(data));
});

    function updateIndividualTotals() {
        const peopleTotals = {};
        const peopleCount = parseInt(peopleCountInput.value);

        for (let i = 1; i <= peopleCount; i++) {
            peopleTotals[i] = 0;
        }

        document.querySelectorAll('.person-item-checkbox:checked').forEach(checkbox => {
            const personId = parseInt(checkbox.dataset.personId);
            const itemContainer = checkbox.closest('.item-container');
            
            const itemPriceInput = itemContainer.querySelector('.item-price-input');
            const itemPrice = parseFloat(itemPriceInput.value);

            if (!isNaN(itemPrice)) {
                peopleTotals[personId] += itemPrice;
            }
        });

        for (let i = 1; i <= peopleCount; i++) {
            const personCard = peopleContainer.querySelector(`.person-card:nth-child(${i})`);
            if (personCard) {
                const totalSpan = personCard.querySelector('.person-total');
                if (totalSpan) {
                    totalSpan.textContent = `Rs${peopleTotals[i].toFixed(2)}`;
                }
            }
        }
    }

    // 🔹 Send data to Flask and redirect on success
    submitBtn.addEventListener('click', function(e) {
        e.preventDefault(); 
        
        const peopleCount = parseInt(peopleCountInput.value);
        const peopleData = [];

        for (let i = 1; i <= peopleCount; i++) {
            const name = document.getElementById(`person_${i}_name`).value.trim();
            const phone = document.getElementById(`person_${i}_number`).value.trim();
            peopleData.push({ person_id: i, name, phone });
        }
        
        const billItems = [];
        document.querySelectorAll('.item-container').forEach(itemContainer => {
            const itemName = itemContainer.querySelector('.item-name').innerText;
            const itemPrice = parseFloat(itemContainer.querySelector('.item-price-input').value);
            billItems.push({
                name: itemName,
                price: itemPrice
            });
        });
        
        const personItems = {};
        document.querySelectorAll('.person-item-checkbox:checked').forEach(checkbox => {
            const personId = parseInt(checkbox.dataset.personId);
            const itemIndex = parseInt(checkbox.dataset.itemIndex);
            if (!personItems[personId]) {
                personItems[personId] = [];
            }
            const itemContainer = checkbox.closest('.item-container');
            const itemName = itemContainer.querySelector('.item-name').innerText;
            personItems[personId].push(itemName);
        });

        // The key change: The fetch call should go to '/calculate', and upon success, redirect.
        fetch('/calculate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                peopleCount,
                people: peopleData,
                items: billItems, 
                personItems: personItems 
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Redirect the browser to the new /results route
                window.location.href = '/results'; 
            } else {
                console.error('Server error:', data.message);
                alert('Error calculating shares: ' + data.message);
            }
        })
        .catch(error => console.error('Error:', error));
    });
});