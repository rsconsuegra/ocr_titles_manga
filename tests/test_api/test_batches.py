import uuid



async def test_create_batch(client, blank_image):
    files = [
        ("files", (f"img_{i}.png", blank_image, "image/png"))
        for i in range(3)
    ]
    response = await client.post("/api/v1/batches", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["total_count"] == 3
    assert data["status"] == "pending"
    assert data["completed_count"] == 0
    assert len(data["runs"]) == 3
    for run in data["runs"]:
        assert run["status"] == "pending"


async def test_create_batch_with_name(client, blank_image):
    files = [("files", ("img.png", blank_image, "image/png"))]
    response = await client.post(
        "/api/v1/batches", files=files, data={"name": "Test Batch"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Batch"


async def test_create_batch_no_files(client):
    response = await client.post("/api/v1/batches", files=[])
    assert response.status_code == 422


async def test_create_batch_too_many_files(client, blank_image):
    files = [
        ("files", (f"img_{i}.png", blank_image, "image/png"))
        for i in range(11)
    ]
    response = await client.post("/api/v1/batches", files=files)
    assert response.status_code == 400
    assert "Maximum 10" in response.json()["detail"]


async def test_list_batches_empty(client):
    response = await client.get("/api/v1/batches")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_batches_after_create(client, blank_image):
    files = [("files", ("img.png", blank_image, "image/png"))]
    await client.post("/api/v1/batches", files=files)

    response = await client.get("/api/v1/batches")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1


async def test_get_batch_detail(client, blank_image):
    files = [("files", ("img.png", blank_image, "image/png"))]
    create_resp = await client.post("/api/v1/batches", files=files)
    batch_id = create_resp.json()["id"]

    response = await client.get(f"/api/v1/batches/{batch_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == batch_id
    assert data["total_count"] == 1
    assert len(data["runs"]) == 1


async def test_get_batch_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/batches/{random_id}")
    assert response.status_code == 404


async def test_trigger_batch_success(client, blank_image):
    files = [("files", ("img.png", blank_image, "image/png"))]
    create_resp = await client.post("/api/v1/batches", files=files)
    batch_id = create_resp.json()["id"]

    response = await client.post(f"/api/v1/batches/{batch_id}/trigger")
    assert response.status_code == 200
    triggered = response.json()
    assert triggered["status"] == "processing"


async def test_trigger_batch_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.post(f"/api/v1/batches/{random_id}/trigger")
    assert response.status_code == 404


async def test_trigger_batch_enqueues_workers(client, blank_image, monkeypatch):
    files = [
        ("files", (f"img_{i}.png", blank_image, "image/png"))
        for i in range(2)
    ]
    create_resp = await client.post("/api/v1/batches", files=files)
    batch_id = create_resp.json()["id"]

    sent_ids = []

    class FakeActor:
        def send(self, run_id):
            sent_ids.append(run_id)

    from ocr_manga_title.api.routes.pipeline import batches as batches_module
    monkeypatch.setattr(batches_module, "process_pipeline_run", FakeActor())

    response = await client.post(f"/api/v1/batches/{batch_id}/trigger")
    assert response.status_code == 200
    assert len(sent_ids) == 2
    assert response.json()["status"] == "processing"
