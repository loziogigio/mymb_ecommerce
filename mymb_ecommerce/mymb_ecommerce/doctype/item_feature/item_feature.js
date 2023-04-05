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
                const data = await file.text();
                const rows = data.split('\n');
                for (let i = 1; i < rows.length; i++) {
                    const cells = rows[i].split(',');

                    const item_feature = frappe.new_doc('Item Feature');
                    item_feature.item_feature = cells[0];
                    item_feature.family_code = cells[1];
                    item_feature.family_name = cells[2];
                    item_feature.erp_family_name = cells[3];

                    // Check if the item exists and link it to the Item Feature
                    frappe.db.get_value('Item', {item_code: item_feature.item_feature}, 'name').then(r => {
                        if (r.name) {
                            item_feature.item = r.name;
                        } else {
                            console.log(`Item ${item_feature.item_feature} not found`);
                        }

                        for (let j = 4; j < cells.length; j++) {
                            const feature_name = rows[0].split(',')[j].toLowerCase();
                            const feature_type = detect_feature_type(cells[j]);
                            const item_feature_value = frappe.model.add_child(item_feature, 'Item Feature Value', 'features');
                            item_feature_value.feature_name = feature_name;
                            item_feature_value.feature_type = feature_type;
                            item_feature_value.value = cells[j].toLowerCase();

                            if (feature_type === 'string') {
                                item_feature_value.string_value = cells[j].toLowerCase();
                            } else if (feature_type === 'int') {
                                item_feature_value.int_value = parseInt(cells[j], 10);
                            } else if (feature_type === 'float') {
                                item_feature_value.float_value = parseFloat(cells[j]);
                            } else if (feature_type === 'boolean') {
                                item_feature_value.boolean_value = cells[j].toLowerCase() === 'true';
                            }
                        }

                        frappe.call({
                            method: 'mymb_ecommerce.mymb_ecommerce.item_feature.add_feature',
                            args: {
                                doc: JSON.stringify(item_feature),
                            },
                            callback: function (response) {
                                console.log(response.message);
                            }
                        });
                    });
                    // debugger
                }
            };
            input.click();
        });
    },
});
