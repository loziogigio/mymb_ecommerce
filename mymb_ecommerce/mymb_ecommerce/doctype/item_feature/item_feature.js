// Helper function to detect the feature type
function detect_feature_type(value) {
    if (value === 'true' || value === 'false') {
        return 'boolean';
    } else if (!isNaN(parseFloat(value)) && isFinite(value)) {
        if (Number.isInteger(parseFloat(value))) {
            return 'int';
        } else {
            return 'float';
        }
    } else {
        return 'string';
    }
}
frappe.ui.form.on("Item Feature", {
    refresh: function (frm) {
        frm.add_custom_button('Import CSV', () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.csv';
            input.onchange = async (e) => {
                const file = e.target.files[0];

                Papa.parse(file, {
                    complete: function (results) {
                        // The 'results' object contains parsed CSV data
                        const rows = results.data;
                        const totalRows = rows.length - 1;

                        // Determine feature types from the first data row (index 1)
                        const featureNames = [];
                        const headerRowCells = rows[0];
                        for (let j = 4; j < headerRowCells.length; j++) {
                            const feature_names = headerRowCells[j].replace(/[\r\n\t]+/g, '').toLowerCase();
                            featureNames.push(feature_names);
                        }
                    
                        // Determine feature types from the first data row (index 1)
                        
                        const featureTypes = [];
                        const firstRowCells = rows[1];
                        const feature_family_code = firstRowCells[1].replace(/[\r\n\t]+/g, '');
                        const feature_family_name = firstRowCells[2].replace(/[\r\n\t]+/g, '');
                        const feature_erp_family_name = firstRowCells[3].replace(/[\r\n\t]+/g, '');
                        for (let j = 4; j < firstRowCells.length; j++) {
                            const feature_value = firstRowCells[j].replace(/[\r\n\t]+/g, '');
                            featureTypes.push(detect_feature_type(feature_value));
                        }

                        // Insert HTML container to display featureNames and featureTypes
                        let container = document.createElement('div');
                        container.className = "features-container";

                        let title = document.createElement('h3');
                        title.innerHTML = `Feature Family Code: ${feature_family_code}, Feature Family Name: ${feature_family_name}`;
                        // Append title
                        container.appendChild(title);

                        let featureUoms = new Array(featureNames.length).fill(''); // Initialize the array to store selected UOMs


                        for (let index = 0; index < featureNames.length; index++) {
                            // Create a row for each feature
                            let row = document.createElement('div');
                            row.className = "row my-2";
                            container.appendChild(row);

                            // Create a column for feature name
                            let nameColumn = document.createElement('div');
                            nameColumn.className = "col-sm-4";
                            row.appendChild(nameColumn);

                            // Create Label for feature name inside nameColumn
                            let label = document.createElement('label');
                            label.className = "control-label";
                            label.innerHTML = featureNames[index];
                            nameColumn.appendChild(label);

                            // Create a column for feature type selector
                            let typeColumn = document.createElement('div');
                            typeColumn.className = "col-sm-4";
                            row.appendChild(typeColumn);

                            // Create a div for control input wrapper inside typeColumn
                            let controlInputWrapper = document.createElement('div');
                            controlInputWrapper.className = "control-input-wrapper";
                            typeColumn.appendChild(controlInputWrapper);

                            // Create select element for feature type inside controlInputWrapper
                            let select = document.createElement('select');
                            select.className = "input-with-feedback form-control";
                            select.setAttribute('data-feature-index', index); // store the index as data attribute
                            controlInputWrapper.appendChild(select);

                            // Add options for select element
                            let types = ['string', 'int', 'float', 'boolean'];
                            types.forEach(type => {
                                let option = document.createElement('option');
                                option.value = type;
                                option.text = type;
                                if (featureTypes[index] === type) {
                                    option.selected = true;
                                }
                                select.appendChild(option);
                            });

                            // Listen for changes on select element
                            select.addEventListener('change', function (event) {
                                let featureIndex = this.getAttribute('data-feature-index');
                                featureTypes[featureIndex] = this.value; // update featureTypes array
                            });

                            // Create a column for UOM selector
                            let uomColumn = document.createElement('div');
                            uomColumn.className = "col-sm-4";
                            row.appendChild(uomColumn);

                            // Create a div for UOM input wrapper inside uomColumn
                            let uomInputWrapper = document.createElement('div');
                            uomInputWrapper.className = "control-input-wrapper";
                            uomColumn.appendChild(uomInputWrapper);

                            // Create select element for UOM inside uomInputWrapper
                            let selectUOM = document.createElement('select');
                            selectUOM.className = "input-with-feedback form-control";
                            selectUOM.setAttribute('data-feature-index', index); // store the index as data attribute
                            uomInputWrapper.appendChild(selectUOM);

                            // Add a default option to the select element
                            let defaultOption = document.createElement('option');
                            defaultOption.value = '';
                            defaultOption.text = 'Select the UOM';
                            selectUOM.appendChild(defaultOption);

                            (async () => {
                                // Fetch the family_uom and default_uom before populating UOM options
                                const familyUOM = await get_family_uom(featureNames[index]);
                                const defaultUOM = await get_default_uom(featureNames[index]);

                                console.log("Family UOM:", familyUOM);
                                console.log("Default UOM:", defaultUOM);
                                
                                // Fetch enabled UOM options from ERPNext and populate the UOM select box
                                let uoms = await frappe.db.get_list('UOM', { fields: ['name'], filters: { enabled: 1 } });
                                console.log("Fetched UOMs:", uoms);

                                let preselectedOption = null;
                                uoms.forEach(uom => {
                                    let option = document.createElement('option');
                                    option.value = uom.name;
                                    option.text = uom.name;
                                    selectUOM.appendChild(option);

                                    // Check if this option should be preselected
                                    if (familyUOM && uom.name === familyUOM) {
                                        preselectedOption = option;
                                    } else if (!familyUOM && defaultUOM && uom.name === defaultUOM) {
                                        preselectedOption = option;
                                    }
                                });
                                console.log("Preselected Option:", preselectedOption);

                                // Preselect the UOM option after populating the options
                                if (preselectedOption) {
                                    preselectedOption.selected = true;
                                }
                            })();

                            // Listen for changes on UOM select element
                            selectUOM.addEventListener('change', function (event) {
                                let featureIndex = this.getAttribute('data-feature-index');
                                featureUoms[featureIndex] = this.value; // update featureUoms array
                            });


                        }

                    // Append the container to the body or any other element you want to attach it to.
                        document.querySelector('.form-column.col-sm-12').appendChild(container);

                        // Create Confirm Button
                        let confirmButton = document.createElement('button');
                        confirmButton.className = "btn btn-primary";
                        confirmButton.innerText = "Confirm Feature Types";
                        confirmButton.style.marginRight = '10px'; // Add some margin between buttons
                        document.querySelector('.form-column.col-sm-12').appendChild(confirmButton);

                        // Create Clear All Button
                        let clearAllButton = document.createElement('button');
                        clearAllButton.className = "btn btn-danger";
                        clearAllButton.innerText = "Clear All";
                        document.querySelector('.form-column.col-sm-12').appendChild(clearAllButton);

                        // On Clear All button click
                        clearAllButton.addEventListener('click', function() {
                            let userConfirmation = confirm("Are you sure you want to clear all? This action cannot be undone.");
                            if (userConfirmation) {
                                // Clear the container
                                container.innerHTML = '';

                                // Remove the buttons
                                confirmButton.remove();
                                clearAllButton.remove();
                                
                                // Clear the variables
                                featureNames.length = 0;
                                featureTypes.length = 0;
                                featureUoms.length = 0;
                            }
                        });
                       // On Confirm button click
                        confirmButton.addEventListener('click', function() {
                            // Start showing progress at 0%
                            let progress = 0;
                            frappe.show_progress(__('Importing Features') , progress);
                            // Simulate progress increase every 0.5 seconds
                            let interval = setInterval(function() {
                                progress += 10; // You can adjust the increment
                                frappe.show_progress(__('Importing Features'), progress);
                                
                                // You may add conditions to stop if progress reaches a certain point, e.g. 90%
                                if (progress >= 90) {
                                    clearInterval(interval);
                                }
                            }, 500); // Update every 0.5 seconds

                            let allItemFeatures = [];

                            // Loop through the rest of the rows for preparing the data
                            for (let i = 1; i < rows.length; i++) {
                                const cells = rows[i];

                                let item_feature = {};
                                item_feature.item_feature = cells[0];
                                item_feature.family_code = feature_family_code;
                                item_feature.family_name = feature_family_name;
                                item_feature.erp_family_name = feature_erp_family_name;
                                item_feature.features = [];

                                for (let j = 4; j < cells.length; j++) {
                                    const feature_value = cells[j].replace(/[\r\n\t]+/g, '');
                                    const feature_type = featureTypes[j - 4];
                                    const feature_name = featureNames[j - 4];
                                    const feature_uom = featureUoms[j - 4];

                                    let item_feature_value = {};
                                    item_feature_value.feature_name = feature_name;
                                    item_feature_value.feature_type = feature_type;
                                    item_feature_value.feature_uom = feature_uom;
                                    item_feature_value.value = feature_value.toLowerCase();

                                    if (feature_type === 'string') {
                                        item_feature_value.string_value = feature_value.toLowerCase();
                                    } else if (feature_type === 'int') {
                                        item_feature_value.int_value = parseInt(feature_value, 10);
                                    } else if (feature_type === 'float') {
                                        item_feature_value.float_value = parseFloat(feature_value);
                                    } else if (feature_type === 'boolean') {
                                        item_feature_value.boolean_value = feature_value.toLowerCase() === 'true';
                                    }

                                    item_feature.features.push(item_feature_value);
                                }

                                allItemFeatures.push(item_feature);
                            }

                            // Send all the item features to the server
                            frappe.call({
                                method: 'mymb_ecommerce.mymb_ecommerce.item_feature.add_feature_list',
                                args: {
                                    docs: JSON.stringify(allItemFeatures),
                                },
                                callback: function(response) {
                                    console.log(response.message);
                                    // Hide progress when the request is done
                                    frappe.hide_progress();

                                    // Clear the progress simulation interval
                                    clearInterval(interval);

                                    // Clear the container
                                    container.innerHTML = '';

                                    // Remove the buttons
                                    confirmButton.remove();
                                    clearAllButton.remove();
                                    
                                    // Clear the variables
                                    featureNames.length = 0;
                                    featureTypes.length = 0;
                                    featureUoms.length = 0;
                                    // Here, show a message to user indicating the import process is completed.
                                    frappe.msgprint({
                                        title: __('Import Completed'),
                                        message: __('The item features have been successfully imported.'),
                                        indicator: 'green'
                                    });
                                }
                            });
                        });
                    }
                });


            };
            input.click();
        });
    },
});

// Function to fetch family_uom for a feature
async function get_family_uom(feature_name) {
    try {
        const result = await frappe.db.get_value('Feature Family', { feature_name: feature_name }, 'family_uom');
        return result && result.message ? result.message.family_uom : null;
    } catch (error) {
        console.error(error);
        return null;
    }
}


// Function to fetch default_uom for a feature
async function get_default_uom(feature_name) {
    try {
        const result = await frappe.db.get_value('Feature Name', { feature_name: feature_name }, 'default_uom');
        return result && result.message ? result.message.default_uom : null;
    } catch (error) {
        console.error(error);
        return null;
    }
}
