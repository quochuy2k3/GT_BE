# Couple API Documentation

## Overview
This API provides endpoints to manage couple relationships between users, including access to partner's today routine and tracker ID.

## Authentication
All endpoints require JWT authentication via the Authorization header:
`Authorization: Bearer <your_jwt_token>`

## Base URL
`/v1/couple`

## Endpoints

### GET /v1/couple/
**Summary:** Get all couples for current user  
**Description:** Get all couples where the authenticated user is a member, with simplified response format

**Response:**
Status: 200 OK  
Content-Type: application/json
```json
[
  {
    "id": "60d5ec9af3b76be4f42c5f92",
    "created_at": "2023-01-01T00:00:00.000Z",
    "partner": {
      "id": "60d5ec9af3b76be4f42c5f91",
      "fullname": "Jane Doe",
      "email": "jane@example.com",
      "avatar": "https://example.com/avatar.jpg",
      "streak": 5,
      "today_tracker_id": "60d5ec9af3b76be4f42c5f94",
      "today_routine": {
        "day_of_week": "Monday",
        "sessions": [
          {
            "status": "pending",
            "time": "08:00 PM",
            "steps": [
              {
                "step_order": 1,
                "step_name": "Cleanser"
              },
              {
                "step_order": 2,
                "step_name": "Toner"
              }
            ]
          }
        ]
      }
    }
  }
]
```

### GET /v1/couple/{couple_id}
**Summary:** Get couple by ID  
**Description:** Get a specific couple by its ID with simplified response format

**Parameters:**
- couple_id (path): The ID of the couple to get

**Response:**
Status: 200 OK  
Content-Type: application/json
```json
{
  "id": "60d5ec9af3b76be4f42c5f92",
  "created_at": "2023-01-01T00:00:00.000Z",
  "partner": {
    "id": "60d5ec9af3b76be4f42c5f91",
    "fullname": "Jane Doe",
    "email": "jane@example.com",
    "avatar": "https://example.com/avatar.jpg",
    "streak": 5,
    "today_tracker_id": "60d5ec9af3b76be4f42c5f94",
    "today_routine": {
      "day_of_week": "Monday",
      "sessions": [
        {
          "status": "pending",
          "time": "08:00 PM",
          "steps": [
            {
              "step_order": 1,
              "step_name": "Cleanser"
            },
            {
              "step_order": 2,
              "step_name": "Toner"
            }
          ]
        }
      ]
    }
  }
}
```

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not authorized to access this couple"
}
```

### 404 Not Found
```json
{
  "detail": "Couple not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "An unexpected error occurred: <error_message>"
}
```

## Note
- Couples are automatically created when a friend request is accepted.
- The `today_tracker_id` field contains only the ID of the partner's tracker for today (if available).
- The `today_routine` field contains only the routine for the current day (similar to the /routine/today endpoint).
- For full tracker details, you can fetch the tracker using the tracker ID from the tracker endpoint. 