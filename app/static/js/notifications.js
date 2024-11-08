// Store displayed notifications IDs
let displayedNotifications = [];

// Add IDs to displayedNotifications array
document.querySelectorAll("[data-notification]").forEach((item) => {
	displayedNotifications.push(item.dataset.notification);
});

// Declare the socket variable globally
let socket;

// Initialize socket if not already initialized
if (!socket) {
	socket = io();
}

$(function () {
	$('[data-bs-toggle="popover"]').popover();
});

// Remove notification badge from 'Messages' link when there are no more unread messages
socket.on("no_unread_messages", function () {
	const unreadBadge = document.getElementById("unread-badge");
	if (unreadBadge) {
		unreadBadge.style.display = "none";
	}
});

// Create notification badge for 'Messages' link when there are new messages
socket.on("new_unread_message", function () {
	const unreadBadge = document.getElementById("unread-badge");

	if (unreadBadge) return;

	const unreadBadgeWrapper = document.getElementById(
		"unread-badge-wrapper"
	);

	const newBadge = document.createElement("div");
	newBadge.innerHTML = `
							<!-- Larger screens -->
							<span
								class="d-none d-md-block position-absolute top-0 start-100 mt-2 translate-middle p-1 bg-danger border border-light rounded-circle">
								<span class="visually-hidden"
									>New messages</span
								>
							</span>
							<!-- Mobile screens -->
							<span
								class="d-block d-md-none ms-1 p-1 bg-danger border border-light rounded-circle">
								<span class="visually-hidden"
									>New messages</span
								>
							</span>
							`;
	unreadBadgeWrapper.appendChild(newBadge);
});

// New notifications
socket.on("notification", function (notification) {
	// Check if the notification has already been displayed
	if (!displayedNotifications.includes(notification.id)) {
		// Update notification badge
		showNotificationBadge();

		// Add to dropdown menu
		const dropdownMenu =
			document.getElementById("dropdown-menu");

		// Remove "No unread notifications" message if present
		const noUnreadMessage = dropdownMenu.querySelector(
			".d-flex.align-items-center.justify-content-center.py-5"
		);
		if (noUnreadMessage) {
			noUnreadMessage.remove();
		}

		const newNotification = createNotification(notification);

		// Insert the new notification
		dropdownMenu.insertBefore(
			newNotification,
			dropdownMenu.children[1]
		);

		// Add notification ID to displayedNotifications
		displayedNotifications.push(notification.id);
	}
});

// Display badge
function showNotificationBadge() {
	const parentBtn = document.getElementById(
		"notificationsDropdown"
	);
	if (!parentBtn.querySelector(".bg-danger")) {
		const span = document.createElement("span");
		span.className =
			"position-absolute top-0 end-0 mt-2 translate-middle-y p-1 bg-danger border border-light rounded-circle";
		span.innerHTML = `<span class="visually-hidden">New notifications</span>`;
		parentBtn.appendChild(span);
	}
}

function hideNotificationBadge() {
	const parentBtn = document.getElementById(
		"notificationsDropdown"
	);
	const badge = parentBtn.querySelector("span");
	if (badge) badge.remove();
}

function updateReadStatus() {
	document
		.querySelectorAll(".notification-item")
		.forEach((link) => {
			link.className =
				"list-group-item notification-item p-3 border text-decoration-none";
		});
}

// Fetch next unread notification
function fetchNextUnreadNotification() {
	fetch("/notifications/next-unread-notification", {
		method: "POST",
		headers: {
			"Content-Type": "application/json",
		},
		body: JSON.stringify(displayedNotifications),
	})
		.then((response) => response.json())
		.then((data) => {
			if (data) {
				const dropdownMenu =
					document.getElementById("dropdown-menu");
				const divider = document.querySelector(
					".notification-divider"
				);

				const newNotification = createNotification(data);
				dropdownMenu.insertBefore(newNotification, divider);

				// After adding a new notification, check if there are no more
				if (displayedNotifications.length === 0) {
					notificationsDisplayBase();
					hideNotificationBadge();
				}
			}
		})
		.catch((error) => {
			console.error("Error:", error.message);
		});
}

// Mark a notification as read
function markAsRead(notificationId, preventDefault = true) {
	if (preventDefault) {
		event.preventDefault();
	}

	fetch(`/notifications/${notificationId}/read`, {
		method: "POST",
	})
		.then((response) => {
			if (!response.ok) {
				return response.json().then((error) => {
					throw new Error(
						error.message || "An error occurred"
					);
				});
			}
			return response.json();
		})
		.then((data) => {
			if (data.status === "success") {
				const notificationElement =
					document.getElementById(notificationId);
				if (notificationElement) {
					notificationElement.remove();
					displayedNotifications =
						displayedNotifications.filter(
							(id) => id !== notificationId
						);
				}

				// After marking a notification as read, check if there are no more
				if (displayedNotifications.length === 0) {
					notificationsDisplayBase();
					hideNotificationBadge();
				}

				// Fetch the next unread notification
				fetchNextUnreadNotification();
			}
		})
		.catch((error) => {
			console.error("Error:", error.message);
			window.location.reload();
		});
}

// Create notification item
function createNotification(notification) {
	const newNotification = document.createElement("li");
	newNotification.id = notification.id;
	newNotification.setAttribute(
		"data-notification",
		notification.id
	);

	newNotification.innerHTML = `
			<a class="dropdown-item notification-item unread" href="${createNotificationLink(
		notification
	)}">
				<img src="${notification.sender_image || "/static/placeholder.jpg"}" alt="${notification.sender_name
		}" class="avatar xs" />
				<div>
					<span class="notification-text">${createNotificationMessage(
			notification
		)}</span>
					<span class="text-muted text-xs fw-light lh-1" title="${notification.created_at
		}">
						${formatTimeAgo(new Date(notification.created_at))}
					</span>
					<button class="border-0 p-0 position-absolute top-50 end-0 translate-middle-y me-2 text-black bg-transparent"
						title="Mark as read"
						onclick="markAsRead('${notification.id}')">
						<i class="fa-regular fa-circle" onmouseenter="this.className='fa-solid fa-circle'" onmouseleave="this.className='fa-regular fa-circle'"></i>
					</button>
				</div>
			</a>`;
	return newNotification;
}

// Mark all notifications as read
function markAllRead() {
	fetch("/notifications/mark-all-read", { method: "POST" })
		.then((response) => {
			if (response.ok) {
				hideNotificationBadge();
				notificationsDisplayBase();
				updateReadStatus();
			}
		})
		.catch((error) => console.error("Error:", error.message));
}

// Display base notifications if none are found
function notificationsDisplayBase() {
	const ul = document.getElementById("dropdown-menu");
	ul.innerHTML = `
			<li class="d-flex align-items-center justify-content-between">
				<h6 class="dropdown-header notification-header fs-6">Notifications</h6>
				<button class="btn btn-link text-muted dropdown-header notification-header" onclick="markAllRead()">Mark all as read</button>
			</li>
			<li class="d-flex align-items-center justify-content-center py-5">
				<h6 class="fw-normal text-muted small">No unread notifications.</h6>
			</li>
			<hr class="dropdown-divider notification-divider" />
			<a class="dropdown-header notification-header text-center" href="/notifications">All notifications</a>`;
}

// Converted codes from helpers.py
// Codes converted by ChatGPT
function formatTimeAgo(date) {
	const now = new Date();
	const diff = now - date;

	// Convert milliseconds to minutes, hours, and days
	const minutes = Math.floor(diff / (1000 * 60));
	const hours = Math.floor(diff / (1000 * 60 * 60));
	const days = Math.floor(diff / (1000 * 60 * 60 * 24));

	// Display minutes ago if less than 1 hour
	if (minutes < 60) {
		return minutes > 1 ? `${minutes}m` : "just now";
	}

	// Display hours ago if less than 24 hours
	else if (hours < 24) {
		return `${hours}h`;
	}

	// Display days ago if within the last 7 days
	else if (days < 7) {
		return `${days}d`;
	}

	// Display as mm-dd-yyyy if older than 7 days
	else {
		return date.toLocaleDateString("en-US", {
			month: "2-digit",
			day: "2-digit",
			year: "numeric",
		});
	}
}

function createNotificationMessage(notification) {
	const senderName = notification.sender_name;

	switch (notification.type) {
		case "friend_request":
			return `${senderName} sent you a friend request`;
		case "friend_accepted":
			return `${senderName} accepted your friend request`;
		case "post_like":
			return `${senderName} liked your post`;
		case "post_comment":
			return `${senderName} commented on your post`;
		case "post_share":
			return `${senderName} shared your post`;
		case "comment_like":
			return `${senderName} liked your comment`;
		default:
			return `New notification from ${senderName}`;
	}
}

function createNotificationLink(notification) {
	switch (notification.type) {
		case "friend_request":
			return "/friends/requests";
		case "friend_accepted":
			return `/profiles/${notification.sender_username}`;
		case "post_like":
			return `/posts/${notification.post_id}`;
		case "post_comment":
			return `/posts/${notification.post_id}#comment-${notification.comment_id}`;
		case "post_share":
			return `/posts/${notification.post_id}`;
		case "comment_like":
			return `/posts/${notification.post_id}#comment-${notification.comment_id}`;
		default:
			return "#";
	}
}