
from typing import Any, Dict, List, Optional

import frappe
from frappe import _
from pytz import timezone

from mymb_ecommerce.repository.MygrxgraRepository import MygrxgraRepository
from datetime import datetime, timedelta , timezone

JsonDict = Dict[str, Any]

@frappe.whitelist(allow_guest=True)
def get_group_tree(**kwargs):
    try:
        filters = kwargs.get("filters")
        csoci = kwargs.get("csoci")
        if not csoci:
            return {"success": False, "error": "Missing csoci parameter"}

        force_refresh = kwargs.get("force_refresh") in ["1", 1, True, "true"]

        cache_key = f"group_tree::{csoci}"
        cached = frappe.cache().get_value(cache_key)

        now = datetime.now(timezone.utc)

        # Check cache validity
        if cached and not force_refresh:
            timestamp = cached.get("timestamp")
            if timestamp:
                timestamp_dt = datetime.fromisoformat(timestamp)
                if now - timestamp_dt < timedelta(hours=1):
                    # Return cached version
                    return {
                        "success": True,
                        "data": cached["data"],
                        "cached": True
                    }

        # If cache is invalid or forced, refresh it
        repo = MygrxgraRepository()
        filters = filters
        records = repo.get_all_records(filters=filters, to_dict=True)

        # Group children by parent ID
        grouped_by_parent = {}
        for item in records:
            parent_id = item["cgrup_darti_r"]
            grouped_by_parent.setdefault(parent_id, []).append(item)

        # Recursive tree builder
        def build_tree(parent_id: str) -> List[Dict[str, Any]]:
            children = grouped_by_parent.get(parent_id, [])
            tree = []
            for child in children:
                group_id = child["cgrup_darti"]
                parent_node = child["cgrup_darti_r"]
                order = child["nlive_dpref"]
                label = child.get("tgrup_darti") or group_id
                node = {
                    "node": group_id,
                    "parent_node": parent_node,
                    "order": order, 
                    "label": label
                }
                if group_id in grouped_by_parent:
                    node["children"] = build_tree(group_id)
                tree.append(node)
            return tree

        tree = build_tree("0")

        # Save refreshed cache
        frappe.cache().set_value(cache_key, {
            "data": tree,
            "timestamp": now.isoformat()
        })

        return {
            "success": True,
            "data": tree,
            "cached": False
        }

    except Exception as e:
        frappe.log_error(title="get_group_tree failed", message=frappe.get_traceback())
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=True)
def find_subtree(**kwargs):
    try:
        csoci = kwargs.get("csoci")
        node = kwargs.get("node")

        if not csoci or not node:
            return {"success": False, "error": "Missing 'csoci' or 'node' parameter"}

                # Reuse the main group tree logic
        args = {'csoci': csoci}
        tree_response = get_group_tree(**args)

        if not tree_response.get("success"):
            return {"success": False, "error": "Failed to load group tree"}

        full_tree = tree_response.get("data", [])

        # Recursive function to locate the node matching `node`
        def search_subtree(tree: List[Dict[str, Any]], target: str) -> Optional[Dict[str, Any]]:
            for node in tree:
                if node["node"] == target:
                    return node
                if "children" in node:
                    result = search_subtree(node["children"], target)
                    if result:
                        return result
            return None

        subtree = search_subtree(full_tree, node)

        if subtree:
            return {
                "success": True,
                "data": subtree
            }
        else:
            return {
                "success": False,
                "error": f"Node '{node}' not found in tree"
            }

    except Exception as e:
        frappe.log_error(title="find_subtree failed", message=frappe.get_traceback())
        return {
            "success": False,
            "error": str(e)
        }
    

def flatten_tree(tree, path=None, flat_paths=None, label_map=None):
    if flat_paths is None:
        flat_paths = {}
    if label_map is None:
        label_map = {}
    if path is None:
        path = []

    for node in tree:
        node_id = node["node"]
        label = node.get("label", node_id)
        current_path = path + [node_id]

        flat_paths[node_id] = current_path
        label_map[node_id] = label

        if "children" in node:
            flatten_tree(node["children"], current_path, flat_paths, label_map)

    return flat_paths, label_map

@frappe.whitelist(allow_guest=True)
def get_flatten_group_tree(**kwargs):
    try:
        csoci = kwargs.get("csoci")
        force_refresh = kwargs.get("force_refresh") in ["1", 1, True, "true"]

        if not csoci:
            return {"success": False, "error": "Missing csoci parameter"}

        cache_key_paths = f"group_flat_paths::{csoci}"
        cache_key_labels = f"group_flat_labels::{csoci}"

        # Try cache
        cached_paths = frappe.cache().get_value(cache_key_paths)
        cached_labels = frappe.cache().get_value(cache_key_labels)

        if cached_paths and cached_labels and not force_refresh:
            return {
                "success": True,
                "cached": True,
                "message": "Flattened group tree loaded from cache",
                "node_count": len(cached_paths),
                "paths": cached_paths,
                "labels": cached_labels
            }

        # Step 1: Get full group tree
        tree_response = get_group_tree(csoci=csoci, force_refresh=force_refresh)
        if not tree_response.get("success"):
            return {"success": False, "error": "Failed to load group tree"}

        tree = tree_response["data"]

        # Step 2: Flatten tree
        def flatten_tree(tree, path=None, flat_paths=None, label_map=None):
            if flat_paths is None:
                flat_paths = {}
            if label_map is None:
                label_map = {}
            if path is None:
                path = []

            for node in tree:
                node_id = node["node"]
                label = node.get("label", node_id)
                current_path = path + [node_id]

                flat_paths[node_id] = current_path
                label_map[node_id] = label

                if "children" in node:
                    flatten_tree(node["children"], current_path, flat_paths, label_map)

            return flat_paths, label_map

        flat_paths, label_map = flatten_tree(tree)

        # Step 3: Cache in frappe.cache
        frappe.cache().set_value(cache_key_paths, flat_paths)
        frappe.cache().set_value(cache_key_labels, label_map)

        return {
            "success": True,
            "cached": False,
            "message": "Flattened group tree saved in cache",
            "node_count": len(flat_paths),
            "paths": flat_paths,
            "labels": label_map
        }

    except Exception as e:
        frappe.log_error(title="get_flatten_group_tree failed", message=frappe.get_traceback())
        return {
            "success": False,
            "error": str(e)
        }

