


document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("taskForm");
    const titleInput = document.getElementById("taskTitle");
    const priorityInput = document.getElementById("taskPriority");
    const dueDateInput = document.getElementById("taskDueDate");
    const taskList = document.getElementById("taskList");
    const emptyMessage = document.getElementById("emptyMessage");

    const totalTasks = document.getElementById("totalTasks");
    const pendingTasks = document.getElementById("pendingTasks");
    const completedTasks = document.getElementById("completedTasks");

    if (!form || !taskList) {
        console.error("TASKDAWG: Task form or task list was not found.");
        return;
    }

    const STORAGE_KEY = "taskdawg_demo_tasks";
    let currentFilter = "all";
    let tasks = loadTasks();

    // Add a category selector without replacing your existing HTML.
    const categoryGroup = document.createElement("div");
    categoryGroup.className = "form-group";

    const categoryLabel = document.createElement("label");
    categoryLabel.htmlFor = "taskCategory";
    categoryLabel.textContent = "Category";

    const categoryInput = document.createElement("select");
    categoryInput.id = "taskCategory";

    ["Study", "Work", "Personal", "Health", "Other"].forEach(category => {
        const option = document.createElement("option");
        option.value = category;
        option.textContent = category;
        categoryInput.appendChild(option);
    });

    categoryGroup.append(categoryLabel, categoryInput);

    const addButton = form.querySelector('button[type="submit"]');
    if (addButton) {
        form.insertBefore(categoryGroup, addButton);
    }

    function loadTasks() {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            const parsed = saved ? JSON.parse(saved) : [];
            return Array.isArray(parsed) ? parsed : [];
        } catch (error) {
            console.error("Could not load saved tasks:", error);
            return [];
        }
    }

    function saveTasks() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
        } catch (error) {
            alert("Your browser could not save the tasks.");
            console.error(error);
        }
    }

    function makeElement(tag, className, text) {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (text !== undefined) element.textContent = text;
        return element;
    }

    function renderTasks() {
        taskList.replaceChildren();

        const visibleTasks = tasks.filter(task => {
            if (currentFilter === "pending") {
                return task.status !== "completed";
            }
            if (currentFilter === "completed") {
                return task.status === "completed";
            }
            return true;
        });

        totalTasks.textContent = tasks.length;
        pendingTasks.textContent =
            tasks.filter(task => task.status !== "completed").length;
        completedTasks.textContent =
            tasks.filter(task => task.status === "completed").length;

        emptyMessage.hidden = visibleTasks.length > 0;

        visibleTasks.forEach(task => {
            const item = makeElement(
                "article",
                "task-item" + (task.status === "completed" ? " completed" : "")
            );

            // Enable dragging to reorder tasks in the list.
            item.draggable = true;
            item.dataset.id = task.id;

            const checkbox = makeElement("input", "task-checkbox");
            checkbox.type = "checkbox";
            checkbox.checked = task.status === "completed";
            checkbox.setAttribute("aria-label", "Mark task completed");

            checkbox.addEventListener("change", () => {
                updateTask(task.id, {
                    status: checkbox.checked ? "completed" : "pending"
                });
            });

            const details = makeElement("div", "task-details");
            const name = makeElement("div", "task-name", task.title);
            const meta = makeElement("div", "task-meta");

            meta.appendChild(
                makeElement("span", "priority " + task.priority, task.priority + " priority")
            );
            meta.appendChild(makeElement("span", "", task.category || "Other"));

            if (task.dueDate) {
                const today = new Date();
                today.setHours(0, 0, 0, 0);

                const due = new Date(task.dueDate + "T00:00:00");
                const isOverdue = due < today && task.status !== "completed";

                meta.appendChild(
                    makeElement(
                        "span",
                        isOverdue ? "overdue-label" : "",
                        (isOverdue ? "Overdue: " : "Due: ") + task.dueDate
                    )
                );
            }

            details.append(name, meta);

            const actions = makeElement("div", "task-actions");

            const editButton = makeElement("button", "edit-btn", "Edit");
            editButton.type = "button";
            editButton.addEventListener("click", () => editTask(task));

            const deleteButton = makeElement("button", "delete-btn", "Delete");
            deleteButton.type = "button";
            deleteButton.addEventListener("click", () => {
                if (confirm("Delete this task?")) {
                    tasks = tasks.filter(item => item.id !== task.id);
                    saveTasks();
                    renderTasks();
                }
            });

            actions.append(editButton, deleteButton);
            item.append(checkbox, details, actions);

            item.addEventListener("dragstart", event => {
                event.dataTransfer.setData("text/plain", task.id);
                event.dataTransfer.effectAllowed = "move";
                item.classList.add("dragging");
            });

            item.addEventListener("dragend", () => {
                item.classList.remove("dragging");
                taskList.querySelectorAll(".drag-over").forEach(element => {
                    element.classList.remove("drag-over");
                });
            });

            item.addEventListener("dragover", event => {
                event.preventDefault();
                item.classList.add("drag-over");
            });

            item.addEventListener("dragleave", () => {
                item.classList.remove("drag-over");
            });

            item.addEventListener("drop", event => {
                event.preventDefault();
                item.classList.remove("drag-over");

                const draggedId = event.dataTransfer.getData("text/plain");
                if (!draggedId || draggedId === task.id) return;

                const fromIndex = tasks.findIndex(t => t.id === draggedId);
                const toIndex = tasks.findIndex(t => t.id === task.id);

                if (fromIndex < 0 || toIndex < 0) return;

                const [movedTask] = tasks.splice(fromIndex, 1);
                tasks.splice(toIndex, 0, movedTask);

                saveTasks();
                renderTasks();
            });

            taskList.appendChild(item);
        });
    }

    function updateTask(id, changes) {
        tasks = tasks.map(task =>
            task.id === id ? { ...task, ...changes } : task
        );
        saveTasks();
        renderTasks();
    }

    function editTask(task) {
        const newTitle = prompt("Edit task name:", task.title);
        if (newTitle === null) return;

        const cleanedTitle = newTitle.trim();
        if (!cleanedTitle) {
            alert("Task name cannot be empty.");
            return;
        }

        const newDueDate = prompt(
            "Enter due date as YYYY-MM-DD, or leave blank:",
            task.dueDate || ""
        );
        if (newDueDate === null) return;

        if (newDueDate && !/^\d{4}-\d{2}-\d{2}$/.test(newDueDate)) {
            alert("Please use the date format YYYY-MM-DD.");
            return;
        }

        updateTask(task.id, {
            title: cleanedTitle,
            dueDate: newDueDate
        });
    }

    form.addEventListener("submit", event => {
        event.preventDefault();

        const title = titleInput.value.trim();
        if (!title) {
            alert("Please enter a task name.");
            titleInput.focus();
            return;
        }

        tasks.unshift({
            id: (crypto.randomUUID
                ? crypto.randomUUID()
                : String(Date.now()) + Math.random().toString(16).slice(2)),
            title: title,
            priority: priorityInput.value,
            category: categoryInput.value,
            dueDate: dueDateInput.value,
            status: "pending",
            createdAt: new Date().toISOString()
        });

        saveTasks();
        form.reset();
        renderTasks();
        titleInput.focus();
    });

    document.querySelectorAll("[data-filter]").forEach(button => {
        button.addEventListener("click", () => {
            currentFilter = button.dataset.filter;

            document.querySelectorAll("[data-filter]").forEach(btn => {
                btn.classList.toggle("selected", btn === button);
            });

            renderTasks();
        });
    });

    renderTasks();
});
