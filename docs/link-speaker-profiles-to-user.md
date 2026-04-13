# Link speaker profiles to an existing user

Admin API to attach **existing** speaker profile documents to a user by setting their `user_id` field.

---

## Endpoint

| | |
|---|---|
| **Method** | `POST` |
| **Path** | `/api/v1/users/{user_id}/link-speaker-profiles` |
| **Auth** | `Authorization: Bearer <JWT>` — caller must be **`admin`** or **`super_admin`** |

---

## Request

**Content-Type:** `application/json`

```json
{
  "speaker_profile_ids": ["<mongo_id_1>", "<mongo_id_2>"]
}
```

- **Required:** at least one non-empty id (after trim).
- **Max:** 200 ids per request.
- Invalid or unknown ids are skipped (see response counts).

---

## Response

Standard `{ "success": true, "data": { ... } }` envelope:

```json
{
  "success": true,
  "data": {
    "speakerProfilesLinked": {
      "matched": 2,
      "modified": 2
    },
    "userId": "<user_id>"
  }
}
```

- **`matched`** — profiles found by `_id` in your list.  
- **`modified`** — documents updated.

---

## Behavior notes

- **Reassignment:** If a profile was already linked to another user, it is **moved** to `{user_id}`.
- **404** — `{user_id}` is not a valid user or user does not exist.
- **Validation errors** — **400** (e.g. empty array).

---

## Related

- Same linking behavior as optional **`speaker_profile_ids`** on **create user** (`POST /api/v1/users` or `POST /api/v1/auth/admin/create-user`).
- **Create** a new profile for a user: `POST /api/v1/users/{user_id}/speaker-profiles` with `{ "full_name": "..." }`.
- **Remove** a profile from a user (delete document): `DELETE /api/v1/users/{user_id}/speaker-profiles/{profile_id}`.
