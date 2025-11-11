let workerCount = 0;

function addWorker() {
    workerCount++;
    const container = document.getElementById("workersContainer");
    const div = document.createElement("div");
    div.classList.add("row", "g-2", "align-items-center", "mb-2");
    div.innerHTML = `
        <div class="col-1"><strong>${workerCount}</strong></div>
        <div class="col-3"><input type="number" class="form-control" placeholder="Розряд" required></div>
        <div class="col-5"><input type="text" class="form-control" placeholder="Обладнання" required></div>
        <div class="col-3"><button type="button" class="btn btn-outline-danger" onclick="removeWorker(this)">Видалити</button></div>
    `;
    container.appendChild(div);
}

function removeWorker(btn) {
    btn.closest('.row').remove();
}

document.getElementById("uploadForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById("csvFile");
    if (!fileInput.files[0]) return alert("Будь ласка, виберіть CSV файл");

    const workers = [];
    document.querySelectorAll("#workersContainer .row").forEach((row, i) => {
        const inputs = row.querySelectorAll("input");
        workers.push({
            id: i + 1,
            grade: inputs[0].value,
            equipment: inputs[1].value
        });
    });

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
    formData.append("workers", JSON.stringify(workers));

    const response = await fetch("/api/process", { method: "POST", body: formData });
    const result = await response.json();

    if (!result.success) {
        alert("Помилка: " + result.error);
        return;
    }

    localStorage.setItem("chronologic_result", JSON.stringify(result.data));

    let html = `<div class="alert alert-success">
        <b>✅ Оброблено!</b><br>
        Загальний час: ${result.total_sum} хв<br>
        Мінімальний можливий час: ${result.max_parallel_time} хв
    </div>`;

    html += `<a href="/result" class="btn btn-primary">Переглянути результат</a>`;
    document.getElementById("resultArea").innerHTML = html;
});