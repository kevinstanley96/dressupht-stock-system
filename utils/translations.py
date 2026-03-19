def get_translations(language="en"):
    """
    Return a dictionary of translations for UI labels.
    Extend this dictionary for additional languages.
    """
    translations = {
        "en": {
            # --- General ---
            "restricted": "You do not have permission to access this section.",
            "not_found": "Item not found in Master Inventory.",
            "error_log": "Error while logging",
            "success": "✅ Logged {qty} units of {name}",
            "showing": "Showing {count} records",
            "no_logs": "No logs found.",

            # --- Arrival ---
            "arrival_header": "📦 Arrival Log",
            "log_stock": "Log New Stock Arrival",
            "sku_input": "Enter SKU",
            "item": "Item",
            "category": "Category",
            "arrival_date": "Arrival Date",
            "quantity": "Quantity",
            "location": "Location",
            "confirm": "Confirm Arrival",
            "history": "Arrival History",

            # --- Inventory ---
            "inventory_header": "📋 Inventory Audit",

            # --- Depot ---
            "depot_header": "🏬 Depot Movements",

            # --- Mannequin ---
            "mannequin_header": "🧍 Mannequin Display",

            # --- Compare ---
            "compare_header": "🔍 Compare Locations",

            # --- Transfer ---
            "transfer_header": "🔄 Transfer Records",

            # --- Sales ---
            "sales_header": "💰 Sales Records",

            # --- Admin ---
            "admin_header": "⚙️ Admin Panel",

            # --- Password ---
            "password_header": "🔑 Change Password",
        },

        # Example French translations
        "fr": {
            "restricted": "Vous n'avez pas la permission d'accéder à cette section.",
            "not_found": "Article introuvable dans l'inventaire principal.",
            "error_log": "Erreur lors de l'enregistrement",
            "success": "✅ {qty} unités de {name} enregistrées",
            "showing": "Affichage de {count} enregistrements",
            "no_logs": "Aucun journal trouvé.",

            "arrival_header": "📦 Journal des arrivées",
            "log_stock": "Enregistrer une nouvelle arrivée",
            "sku_input": "Entrer le SKU",
            "item": "Article",
            "category": "Catégorie",
            "arrival_date": "Date d'arrivée",
            "quantity": "Quantité",
            "location": "Emplacement",
            "confirm": "Confirmer l'arrivée",
            "history": "Historique des arrivées",

            "inventory_header": "📋 Audit d'inventaire",
            "depot_header": "🏬 Mouvements du dépôt",
            "mannequin_header": "🧍 Présentation sur mannequin",
            "compare_header": "🔍 Comparer les emplacements",
            "transfer_header": "🔄 Transferts",
            "sales_header": "💰 Ventes",
            "admin_header": "⚙️ Panneau d'administration",
            "password_header": "🔑 Changer le mot de passe",
        }
    }

    return translations.get(language, translations["en"])
