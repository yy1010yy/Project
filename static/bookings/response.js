<div id="booking-error" class="alert alert-danger d-none"></div>


const response = await fetch("/booking/create", {
    method: "POST",
    body: formData
});

if (!response.ok) {
    const data = await response.json();

    if (data.error === "room_unavailable") {
        const error = document.querySelector("#booking-error");

        error.textContent = data.message;
        error.classList.remove("d-none");

        setTimeout(() => {
            window.location.href =
                `/rooms/search?roomType=${encodeURIComponent(roomType)}` +
                `&check_in=${encodeURIComponent(checkIn)}` +
                `&check_out=${encodeURIComponent(checkOut)}`;
        }, 1500);
    }
}
