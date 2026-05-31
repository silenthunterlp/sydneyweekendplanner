TOOLS: list[dict] = [
    {
        "name": "get_weather",
        "description": (
            "Get Sydney weather forecast for a date range. "
            "Returns temperature, precipitation probability, UV index, and weather description per day."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "search_events",
        "description": (
            "Search for events happening in Sydney on given dates. "
            "Returns event name, venue, suburb, cost, and URL."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
                "category": {
                    "type": "string",
                    "enum": ["outdoor", "arts", "food", "sports", "family", "music", "markets", "nightlife", "any"],
                    "description": "Event category filter",
                },
                "suburb": {"type": "string", "description": "Sydney suburb name or 'any'"},
                "max_price_aud": {"type": "number", "description": "Maximum ticket price in AUD. Use 0 for free events only."},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_transport_options",
        "description": (
            "Get public transport journey options between two Sydney suburbs, "
            "including estimated duration and Opal fare."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "origin_suburb": {"type": "string", "description": "Starting Sydney suburb"},
                "destination_suburb": {"type": "string", "description": "Destination Sydney suburb"},
                "departure_datetime": {"type": "string", "description": "ISO datetime YYYY-MM-DDTHH:MM"},
            },
            "required": ["origin_suburb", "destination_suburb", "departure_datetime"],
        },
    },
    {
        "name": "get_user_preferences",
        "description": "Retrieve the stored preferences for the current user, including interests, budget, home suburb, and group type.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "save_user_preferences",
        "description": "Persist updated user preferences to the database. Pass only the fields that have changed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "preferences": {
                    "type": "object",
                    "description": (
                        "Partial preference fields to update. Valid keys: "
                        "home_suburb, budget_per_day_aud, interests (list), "
                        "preferred_transport, group_type, children_ages (list), "
                        "avoids_rain, accessibility_needs, max_travel_time_minutes, "
                        "prefers_early_start, onboarding_complete."
                    ),
                },
            },
            "required": ["user_id", "preferences"],
        },
    },
]
