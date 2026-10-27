from conftest import register


# ------------------------------------------------------------------------- auth


def test_register_login_and_me(client):
    r = client.post(
        "/api/auth/register",
        json={"name": "  Ana  ", "email": "Ana@Example.com", "password": "secret123"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "ana@example.com"  # lowercased
    assert body["user"]["name"] == "Ana"  # trimmed
    assert "password" not in str(body)

    r = client.post("/api/auth/login", json={"email": "ANA@example.com", "password": "secret123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "ana@example.com"


def test_duplicate_email_rejected(client):
    register(client)
    r = client.post(
        "/api/auth/register",
        json={"name": "Other", "email": "ana@example.com", "password": "secret123"},
    )
    assert r.status_code == 409


def test_register_validation(client):
    bad = [
        {"name": "A", "email": "not-an-email", "password": "secret123"},
        {"name": "A", "email": "a@example.com", "password": "short"},
        {"name": "A", "email": "a@example.com", "password": "x" * 73},
        {"name": "   ", "email": "a@example.com", "password": "secret123"},
    ]
    for payload in bad:
        assert client.post("/api/auth/register", json=payload).status_code == 422, payload


def test_login_failures_are_generic(client):
    register(client)
    wrong_pw = client.post("/api/auth/login", json={"email": "ana@example.com", "password": "nope!!"})
    no_user = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "nope!!"})
    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


def test_protected_routes_need_a_valid_token(client):
    assert client.get("/api/tasks").status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    bad = {"Authorization": "Bearer not.a.token"}
    assert client.get("/api/tasks", headers=bad).status_code == 401


# ------------------------------------------------------------------------- tasks


def test_task_crud(client, auth):
    r = client.post("/api/tasks", headers=auth, json={"title": "  Write report  "})
    assert r.status_code == 201
    task = r.json()
    assert task["title"] == "Write report"
    assert task["priority"] == "medium"
    assert task["status"] == "pending"
    assert task["category"] == "Other"
    assert task["due_date"] is None
    tid = task["id"]

    r = client.get(f"/api/tasks/{tid}", headers=auth)
    assert r.status_code == 200

    r = client.patch(
        f"/api/tasks/{tid}",
        headers=auth,
        json={"status": "completed", "priority": "high", "category": "Work"},
    )
    assert r.status_code == 200
    assert (r.json()["status"], r.json()["priority"], r.json()["category"]) == (
        "completed",
        "high",
        "Work",
    )
    assert r.json()["title"] == "Write report"  # untouched fields stay

    assert client.delete(f"/api/tasks/{tid}", headers=auth).status_code == 204
    assert client.get(f"/api/tasks/{tid}", headers=auth).status_code == 404


def test_front_end_style_values_are_accepted(client, auth):
    """The task form sends Normal/High/Low and a plain YYYY-MM-DD date (or blank)."""
    r = client.post(
        "/api/tasks",
        headers=auth,
        json={"title": "Pay rent", "priority": "Normal", "due_date": "2030-01-15", "category": "Personal"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["priority"] == "medium"
    assert r.json()["due_date"].startswith("2030-01-15")

    assert client.post(
        "/api/tasks", headers=auth, json={"title": "x", "priority": "HIGH", "due_date": ""}
    ).json()["priority"] == "high"

    tid = r.json()["id"]
    r = client.patch(f"/api/tasks/{tid}", headers=auth, json={"due_date": ""})
    assert r.status_code == 200
    assert r.json()["due_date"] is None


def test_task_validation(client, auth):
    assert client.post("/api/tasks", headers=auth, json={"title": "   "}).status_code == 422
    assert client.post("/api/tasks", headers=auth, json={"title": "x" * 201}).status_code == 422
    assert client.post("/api/tasks", headers=auth, json={"title": "x", "priority": "urgent"}).status_code == 422
    assert client.post("/api/tasks", headers=auth, json={"title": "x", "status": "done"}).status_code == 422
    tid = client.post("/api/tasks", headers=auth, json={"title": "ok"}).json()["id"]
    assert client.patch(f"/api/tasks/{tid}", headers=auth, json={"title": None}).status_code == 422


def test_users_cannot_see_or_touch_each_others_tasks(client):
    ana = register(client, "ana@example.com")
    bob = register(client, "bob@example.com", name="Bob")
    tid = client.post("/api/tasks", headers=ana, json={"title": "Ana's secret"}).json()["id"]

    assert client.get("/api/tasks", headers=bob).json() == []
    assert client.get(f"/api/tasks/{tid}", headers=bob).status_code == 404
    assert client.patch(f"/api/tasks/{tid}", headers=bob, json={"title": "hacked"}).status_code == 404
    assert client.delete(f"/api/tasks/{tid}", headers=bob).status_code == 404
    assert client.post("/api/tasks/reorder", headers=bob, json={"ids": [tid]}).status_code == 400

    assert client.get(f"/api/tasks/{tid}", headers=ana).json()["title"] == "Ana's secret"


def test_filters_and_stats(client, auth):
    a = client.post("/api/tasks", headers=auth, json={"title": "a"}).json()["id"]
    b = client.post("/api/tasks", headers=auth, json={"title": "b", "status": "in_progress"}).json()["id"]
    c = client.post("/api/tasks", headers=auth, json={"title": "c", "status": "completed"}).json()["id"]
    client.post("/api/tasks", headers=auth, json={"title": "late", "due_date": "2000-01-01"})
    client.post(
        "/api/tasks",
        headers=auth,
        json={"title": "late but done", "due_date": "2000-01-01", "status": "completed"},
    )

    def ids(f):
        return {t["id"] for t in client.get("/api/tasks", headers=auth, params={"filter": f}).json()}

    assert len(ids("all")) == 5
    assert c in ids("completed") and a not in ids("completed")
    assert b in ids("in_progress") and len(ids("in_progress")) == 1
    assert c not in ids("pending") and {a, b} <= ids("pending") and len(ids("pending")) == 3

    stats = client.get("/api/tasks/stats", headers=auth).json()
    assert stats == {"total": 5, "pending": 3, "in_progress": 1, "completed": 2, "overdue": 1}

    assert client.get("/api/tasks", headers=auth, params={"filter": "bogus"}).status_code == 422


def test_empty_stats(client, auth):
    assert client.get("/api/tasks/stats", headers=auth).json() == {
        "total": 0, "pending": 0, "in_progress": 0, "completed": 0, "overdue": 0,
    }


def test_new_tasks_go_on_top_and_reorder_persists(client, auth):
    first = client.post("/api/tasks", headers=auth, json={"title": "first"}).json()["id"]
    second = client.post("/api/tasks", headers=auth, json={"title": "second"}).json()["id"]
    third = client.post("/api/tasks", headers=auth, json={"title": "third"}).json()["id"]

    def order():
        return [t["id"] for t in client.get("/api/tasks", headers=auth).json()]

    assert order() == [third, second, first]

    r = client.post("/api/tasks/reorder", headers=auth, json={"ids": [first, third, second]})
    assert r.status_code == 204
    assert order() == [first, third, second]

    # A new task still lands on top after a manual reorder.
    fourth = client.post("/api/tasks", headers=auth, json={"title": "fourth"}).json()["id"]
    assert order()[0] == fourth

    assert client.post("/api/tasks/reorder", headers=auth, json={"ids": [first, first]}).status_code == 422
    assert client.post("/api/tasks/reorder", headers=auth, json={"ids": [999999]}).status_code == 400


# ------------------------------------------------------------------------- contact


def test_contact_form(client):
    payload = {"name": "Sam", "email": "sam@example.com", "subject": "Hi", "message": "Love the app."}
    assert client.post("/api/contact", json=payload).status_code == 201
    assert client.post("/api/contact", json={**payload, "email": "nope"}).status_code == 422
    assert client.post("/api/contact", json={**payload, "message": "  "}).status_code == 422


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}
