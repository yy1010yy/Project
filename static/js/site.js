"use strict";

const menuButton = document.querySelector("[data-menu-toggle]");
menuButton?.addEventListener("click", () => {
  const menu = document.getElementById(menuButton.getAttribute("aria-controls"));
  const open = menuButton.getAttribute("aria-expanded") !== "true";
  menuButton.setAttribute("aria-expanded", String(open));
  menu.dataset.open = String(open);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && menuButton?.getAttribute("aria-expanded") === "true") {
    menuButton.click();
    menuButton.focus();
  }
});

document.querySelectorAll("[data-password-toggle]").forEach((button) => {
  button.addEventListener("click", () => {
    const field = document.getElementById(button.dataset.passwordToggle);
    const show = field.type === "password";
    field.type = show ? "text" : "password";
    button.textContent = show ? "Hide password" : "Show password";
    button.setAttribute("aria-pressed", String(show));
  });
});

document.querySelectorAll("[data-password-confirm]").forEach((form) => {
  const password = form.elements.new_password || form.elements.password;
  const confirmation = form.elements.confirm_password;
  const validate = () => confirmation.setCustomValidity(
    confirmation.value && confirmation.value !== password.value ? "The passwords do not match." : ""
  );
  password.addEventListener("input", validate);
  confirmation.addEventListener("input", validate);
});

document.querySelectorAll("dialog").forEach((dialog) => {
  if (!dialog.hasAttribute("aria-label")) dialog.setAttribute("aria-label", dialog.querySelector("h2").textContent);
});
document.querySelectorAll("[data-dialog-open]").forEach((button) => {
  button.addEventListener("click", () => document.getElementById(button.dataset.dialogOpen).showModal());
});
document.querySelectorAll("[data-dialog-close]").forEach((button) => {
  button.addEventListener("click", () => button.closest("dialog").close());
});

function showError(container, message) {
  const element = container.querySelector("[data-form-error]");
  element.textContent = message;
  element.hidden = !message;
  if (message) {
    element.tabIndex = -1;
    element.focus();
  }
}

async function readResponse(response) {
  if (response.redirected && ["/login", "/change_password"].includes(new URL(response.url).pathname)) {
    window.location.assign(response.url);
    return null;
  }
  const isJSON = response.headers.get("content-type")?.includes("application/json");
  const data = isJSON ? await response.json() : null;
  if (!response.ok || data?.success === false) {
    throw new Error(data?.error || (response.status === 403 ? "Your account cannot perform this action." : "We couldn't save that change. Please try again."));
  }
  if (!data) throw new Error("The server returned an unexpected response. Please try again.");
  return data;
}

document.querySelectorAll("[data-api-form]").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (form.dataset.busy === "true") return;
    const button = form.querySelector("button[type=submit]");
    const label = button.textContent;
    const formData = new FormData(form);
    form.dataset.busy = "true";
    button.disabled = true;
    button.textContent = "Saving…";
    showError(form, "");
    try {
      const data = await readResponse(await fetch(form.action, {
        method: "POST", body: formData, headers: { "Accept": "application/json" },
      }));
      if (!data) return;
      if (form.dataset.success === "reload") {
        // Session storage carries only a human-readable notice, never credentials.
        try {
          sessionStorage.setItem("courtyard-notice", data.message || "Changes saved.");
        } catch {
          // Saving still succeeds when browser storage is unavailable.
        }
        window.location.reload();
        return;
      }
      const panel = form.parentElement.querySelector("[data-success-panel]");
      if (form.dataset.success === "credentials") {
        panel.querySelector("[data-temporary-password]").textContent = data.temporary_password;
        const id = panel.querySelector("[data-employee-id]");
        if (id) id.textContent = data.employee_id;
      }
      if (form.dataset.success !== "saved") form.hidden = true;
      panel.hidden = false;
      panel.focus();
    } catch (error) {
      showError(form, error instanceof TypeError ? "We couldn't connect. Check your connection and try again." : error.message);
    } finally {
      form.dataset.busy = "false";
      button.disabled = false;
      button.textContent = label;
    }
  });
});

document.querySelectorAll("[data-copy-password]").forEach((button) => {
  button.addEventListener("click", async () => {
    const panel = button.closest("[data-success-panel]");
    const status = panel.querySelector("[data-copy-status]");
    try {
      await navigator.clipboard.writeText(panel.querySelector("[data-temporary-password]").textContent);
      status.textContent = "Temporary password copied.";
    } catch {
      status.textContent = "Copy isn't available in this browser. Select and copy the password above.";
    }
  });
});

let storedNotice;
try {
  storedNotice = sessionStorage.getItem("courtyard-notice");
  sessionStorage.removeItem("courtyard-notice");
} catch {
  // Notices are optional; navigation and booking must still work.
}
if (storedNotice) {
  const notice = document.createElement("div");
  notice.className = "notice notice-success shell mt-6";
  notice.setAttribute("role", "status");
  notice.textContent = storedNotice;
  document.getElementById("main").prepend(notice);
}

document.querySelectorAll("[data-table-filter]").forEach((input) => {
  input.addEventListener("input", () => {
    const container = document.getElementById(input.dataset.tableFilter);
    const rows = [...container.querySelectorAll("tbody tr")];
    const query = input.value.trim().toLocaleLowerCase();
    rows.forEach((row) => { row.hidden = !row.textContent.toLocaleLowerCase().includes(query); });
    container.querySelector("[data-no-matches]").hidden = !rows.length || rows.some((row) => !row.hidden);
  });
});

function element(tag, className, text) {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (text !== undefined) result.textContent = text;
  return result;
}

const searchForm = document.querySelector("[data-room-search]");
if (searchForm) {
  const presentation = JSON.parse(document.getElementById("room-presentation").textContent);
  const container = document.querySelector("[data-room-results]");
  const status = document.querySelector("[data-search-status]");
  const arrival = searchForm.elements.check_in;
  const departure = searchForm.elements.check_out;
  const searchButton = searchForm.querySelector("button[type=submit]");
  const currency = new Intl.NumberFormat("en-MY", { style: "currency", currency: "MYR" });
  let controller;
  let sequence = 0;

  const validateDates = () => {
    if (arrival.value) {
      const nextDay = new Date(`${arrival.value}T00:00:00Z`);
      nextDay.setUTCDate(nextDay.getUTCDate() + 1);
      departure.min = nextDay.toISOString().slice(0, 10);
    }
    departure.setCustomValidity(departure.value && arrival.value && departure.value <= arrival.value ? "Departure must be after arrival." : "");
  };
  arrival.addEventListener("input", validateDates);
  departure.addEventListener("input", validateDates);

  function renderRoom(room, dates) {
    const story = presentation.stories[room.room_type] || { name: "Room", image: "room", description: "A welcoming place to stay." };
    const image = presentation.images[story.image];
    const article = element("article", "room-tile");
    const photo = element("img");
    photo.src = presentation.assetBase + image.file;
    photo.alt = image.alt;
    photo.loading = "lazy";
    photo.width = 1536;
    photo.height = 1024;
    const details = element("div", "flex flex-col justify-center md:pl-6");
    const heading = element("h2", "text-4xl", story.name);
    details.append(heading, element("p", "mt-3 text-sm text-fern", `Room ${room.room_number}`), element("p", "mt-5 text-fern", story.description));
    const nights = Math.round((new Date(dates.checkout) - new Date(dates.checkin)) / 86400000);
    const rate = element("p", "mt-6 font-display text-3xl", currency.format(room.room_price));
    rate.append(element("span", "ml-2 font-sans text-sm text-fern", "per night"));
    details.append(rate, element("p", "mt-2 text-sm text-fern", `${nights} ${nights === 1 ? "night" : "nights"} · room subtotal ${currency.format(room.room_price * nights)}`));
    const form = element("form", "mt-7");
    form.method = "POST";
    form.action = searchForm.dataset.startUrl;
    for (const [name, value] of Object.entries({ room_id: room.id, checkin_date: dates.checkin, checkout_date: dates.checkout })) {
      const input = element("input");
      input.type = "hidden";
      input.name = name;
      input.value = value;
      form.append(input);
    }
    const button = element("button", "button button-secondary", "Choose this room");
    button.type = "submit";
    button.setAttribute("aria-label", `Choose ${story.name}, room ${room.room_number}`);
    form.append(button);
    details.append(form);
    article.append(photo, details);
    return article;
  }

  searchForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    validateDates();
    if (!searchForm.reportValidity()) return;
    controller?.abort();
    controller = new AbortController();
    const currentSequence = ++sequence;
    const dates = { checkin: arrival.value, checkout: departure.value };
    const query = new URLSearchParams(new FormData(searchForm));
    container.replaceChildren();
    container.setAttribute("aria-busy", "true");
    searchButton.disabled = true;
    searchButton.textContent = "Finding rooms…";
    status.textContent = "Checking the reservation book…";
    showError(searchForm.parentElement, "");
    try {
      const data = await readResponse(await fetch(`${searchForm.dataset.searchUrl}?${query}`, { signal: controller.signal }));
      if (!data || currentSequence !== sequence) return;
      document.querySelector("[data-room-intro]").hidden = true;
      const currentURL = new URL(window.location.href);
      currentURL.search = query.toString();
      window.history.replaceState({}, "", currentURL);
      status.textContent = `${data.rooms.length} ${data.rooms.length === 1 ? "room" : "rooms"} available for your dates.`;
      if (data.rooms.length) data.rooms.forEach((room) => container.append(renderRoom(room, dates)));
      else {
        const empty = element("section", "empty");
        empty.append(element("h2", "text-3xl", "A full house for those dates."), element("p", "text-fern", "Try another arrival date, a shorter stay or a different room type."));
        container.append(empty);
      }
    } catch (error) {
      if (error.name === "AbortError" || currentSequence !== sequence) return;
      status.textContent = "Availability could not be checked.";
      showError(searchForm.parentElement, error instanceof TypeError ? "We couldn't connect. Please try again." : error.message);
    } finally {
      if (currentSequence === sequence) {
        searchButton.disabled = false;
        searchButton.textContent = "Find available rooms";
        container.setAttribute("aria-busy", "false");
      }
    }
  });
  validateDates();
  if (arrival.value && departure.value) searchForm.requestSubmit();
}
