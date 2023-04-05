frappe.ui.form.on('Item Feature', {
    refresh: function (frm) {
      // Add a custom button to the form to trigger the import
      frm.add_custom_button('Import CSV', () => {
        // Read the CSV file
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.csv';
        input.onchange = async (e) => {
          const file = e.target.files[0];
          const data = await file.text();
          const rows = data.split('\n');
          // Loop through the rows, skipping the header
          for (let i = 1; i < rows.length; i++) {
            const cells = rows[i].split(',');
  
            // Create a new "Item Feature" document
            const item_feature = frappe.new_doc('Item Feature');
            item_feature.item = cells[0]; // Map the Item field
            item_feature.family_code = cells[1]; // Map the Family Code field
            item_feature.family_name = cells[2]; // Map the Family Name field
            item_feature.erp_family_name = cells[3]; // Map the ERP Family Name field
  
            // Loop through the remaining columns and create "Item Feature Value" child records
            for (let j = 4; j < cells.length; j++) {
              const item_feature_value = frappe.new_doc('Item Feature Value');
              item_feature_value.feature_name = 'YOUR_FEATURE_NAME'; // Set the feature name
              item_feature_value.feature_type = 'YOUR_FEATURE_TYPE'; // Set the feature type
              // Set the appropriate value field based on the feature type
              if (item_feature_value.feature_type === 'string') {
                item_feature_value.string_value = cells[j];
              } else if (item_feature_value.feature_type === 'int') {
                item_feature_value.int_value = parseInt(cells[j], 10);
              } else if (item_feature_value.feature_type === 'float') {
                item_feature_value.float_value = parseFloat(cells[j]);
              } else if (item_feature_value.feature_type === 'boolean') {
                item_feature_value.boolean_value = cells[j].toLowerCase() === 'true';
              }
              // Add the "Item Feature Value" record to the "Item Feature" parent document
              item_feature.append('features', item_feature_value);
            }
  
            // Save the "Item Feature" document
            frappe.call({
              method: 'frappe.client.insert',
              args: {
                doc: item_feature,
              },
            });
          }
        };
        input.click();
      });
    },
  });
  