frappe.listview_settings['Item Feature'] = {
  onload: function (listview) {
      listview.page.add_menu_item('Import CSV', () => {
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
                  item_feature.item = cells[0];
                  item_feature.family_code = cells[1];
                  item_feature.family_name = cells[2];
                  item_feature.erp_family_name = cells[3];

                  for (let j = 4; j < cells.length; j++) {
                      const item_feature_value = frappe.new_doc('Item Feature Value');
                      item_feature_value.feature_name = 'YOUR_FEATURE_NAME';
                      item_feature_value.feature_type = 'YOUR_FEATURE_TYPE';

                      if (item_feature_value.feature_type === 'string') {
                          item_feature_value.string_value = cells[j];
                      } else if (item_feature_value.feature_type === 'int') {
                          item_feature_value.int_value = parseInt(cells[j], 10);
                      } else if (item_feature_value.feature_type === 'float') {
                          item_feature_value.float_value = parseFloat(cells[j]);
                      } else if (item_feature_value.feature_type === 'boolean') {
                          item_feature_value.boolean_value = cells[j].toLowerCase() === 'true';
                      }

                      item_feature.append('features', item_feature_value);
                  }

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
};
