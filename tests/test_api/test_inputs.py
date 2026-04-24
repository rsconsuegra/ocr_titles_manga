import io
import uuid


async def test_upload_single_image(client, blank_image):
    response = await client.post(
        "/api/v1/inputs/upload",
        files=[("files", ("test.png", blank_image, "image/png"))],
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "pending"
    assert data[0]["input_image_path"]


async def test_upload_multiple_images(client, blank_image):
    files = [("files", (f"img_{i}.png", blank_image, "image/png")) for i in range(3)]
    response = await client.post("/api/v1/inputs/upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


async def test_upload_invalid_extension(client):
    fake_file = io.BytesIO(b"not an image")
    response = await client.post(
        "/api/v1/inputs/upload",
        files=[("files", ("test.gif", fake_file, "image/gif"))],
    )
    assert response.status_code == 400
    assert "Invalid format" in response.json()["detail"]


async def test_upload_too_many_files(client, blank_image):
    files = [("files", (f"img_{i}.png", blank_image, "image/png")) for i in range(11)]
    response = await client.post("/api/v1/inputs/upload", files=files)
    assert response.status_code == 400
    assert "Maximum 10" in response.json()["detail"]


async def test_upload_file_too_large(client):
    big_content = b"x" * (21 * 1024 * 1024)
    big_file = io.BytesIO(big_content)
    response = await client.post(
        "/api/v1/inputs/upload",
        files=[("files", ("big.png", big_file, "image/png"))],
    )
    assert response.status_code == 400
    assert "too large" in response.json()["detail"].lower()


async def test_get_input_after_upload(client, blank_image):
    response = await client.post(
        "/api/v1/inputs/upload",
        files=[("files", ("test.png", blank_image, "image/png"))],
    )
    run_id = response.json()[0]["id"]

    response = await client.get(f"/api/v1/inputs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run_id
    assert data["status"] == "pending"


async def test_get_input_not_found(client):
    random_id = str(uuid.uuid4())
    response = await client.get(f"/api/v1/inputs/{random_id}")
    assert response.status_code == 404
