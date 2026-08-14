import { clearToken, hasToken } from "./api.js";
import { getCurrentUser, login, registerAccount } from "./auth.js";
import { createBook, deleteBook, fetchBooks, updateBook } from "./books.js";
import { borrowBook, fetchBorrowRecords, returnBook } from "./borrows.js";
import {
  $,
  $$,
  escapeHtml,
  formatDate,
  hideModal,
  initials,
  setLoading,
  showModal,
  showToast,
} from "./ui.js";

const state = {
  user: null,
  books: [],
  records: [],
  cacheStatus: "—",
  search: "",
  availability: "all",
  pendingDeleteId: null,
};

const isAdmin = () => state.user?.role === "admin";
const bookById = (bookId) => state.books.find((book) => book.id === Number(bookId));

function switchAuthTab(tab) {
  const isLogin = tab === "login";
  $("#login-form").classList.toggle("hidden", !isLogin);
  $("#register-form").classList.toggle("hidden", isLogin);
  $("#auth-title").textContent = isLogin
    ? "Sign in"
    : "Create member account";
  $("#auth-subtitle").textContent = isLogin
    ? "Enter your email and password."
    : "Fill in the form to register as a member.";

  $$('[data-auth-tab]').forEach((button) => {
    const active = button.dataset.authTab === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
}

function renderSession() {
  const loggedIn = Boolean(state.user);
  $("#auth-screen").classList.toggle("hidden", loggedIn);
  $("#app-shell").classList.toggle("hidden", !loggedIn);
  if (!loggedIn) return;

  const admin = isAdmin();
  $("#user-name").textContent = state.user.full_name;
  $("#user-role").textContent = admin ? "Administrator" : "Library member";
  $("#user-avatar").textContent = initials(state.user.full_name);
  $("#greeting").textContent = `Welcome, ${state.user.full_name.split(" ")[0]}`;
  $("#history-nav-label").textContent = admin ? "Borrowing Records" : "My Borrowing";
  $("#history-title").textContent = admin ? "Borrowing Records" : "My Borrowing History";
  $("#history-subtitle").textContent = admin
    ? "View active and returned records."
    : "View your borrowed and returned books.";

  $$(".admin-only").forEach((element) => element.classList.toggle("hidden", !admin));
  $$(".admin-only-cell").forEach((element) => element.classList.toggle("hidden", !admin));
  $$(".member-only-cell").forEach((element) => element.classList.toggle("hidden", admin));
}

function showView(viewName) {
  $$(".view-section").forEach((section) => section.classList.add("hidden"));
  $(`#${viewName}-view`).classList.remove("hidden");
  $$(".nav-item[data-view]").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === viewName);
  });
  $("#sidebar").classList.remove("open");

  if (viewName === "history") {
    loadHistory();
  }
  if (viewName === "books") {
    $("#catalog-search").focus();
  }
}

function bookCell(book) {
  return `<span class="book-cell"><span class="book-cover">▤</span><span><strong title="${escapeHtml(book.title)}">${escapeHtml(book.title)}</strong><small>${escapeHtml(book.author)}</small></span></span>`;
}

function statusBadge(book) {
  if (book.available_copies < 1) return '<span class="badge badge-danger">Unavailable</span>';
  if (book.available_copies <= Math.max(1, Math.floor(book.total_copies / 3))) {
    return '<span class="badge badge-warning">Low stock</span>';
  }
  return '<span class="badge badge-success">Available</span>';
}

function renderStats() {
  const titles = state.books.length;
  const copies = state.books.reduce((total, book) => total + book.total_copies, 0);
  const available = state.books.reduce((total, book) => total + book.available_copies, 0);
  const loans = copies - available;
  const rate = copies ? Math.round((available / copies) * 100) : 0;

  $("#stat-titles").textContent = titles;
  $("#stat-copies").textContent = copies;
  $("#stat-available").textContent = available;
  $("#stat-loans").textContent = loans;
  $("#availability-rate").textContent = `${rate}% availability`;
  $("#donut-rate").textContent = `${rate}%`;
  $("#availability-donut").style.background = `conic-gradient(var(--primary) ${rate}%, #e8ece9 ${rate}%)`;
  $("#availability-title").textContent = titles
    ? `Available copies: ${available} of ${copies}`
    : "No books have been added yet";
  $("#availability-description").textContent = `Borrowed copies: ${loans}. Counts are updated after every borrow or return.`;

  const cacheBadge = $("#cache-badge");
  cacheBadge.textContent = `Cache ${state.cacheStatus}`;
  cacheBadge.className = `badge ${state.cacheStatus === "HIT" ? "badge-success" : "badge-neutral"}`;
}

function renderOverviewBooks() {
  const books = [...state.books]
    .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
    .slice(0, 5);

  $("#overview-books-body").innerHTML = books.length
    ? books.map((book) => `<tr><td>${bookCell(book)}</td><td>${escapeHtml(book.isbn)}</td><td><strong>${book.available_copies}/${book.total_copies}</strong><div class="availability-bar"><span style="width:${Math.round((book.available_copies / book.total_copies) * 100)}%"></span></div></td><td>${statusBadge(book)}</td></tr>`).join("")
    : '<tr><td class="empty-state" colspan="4">No books have been added yet.</td></tr>';
}

function filteredBooks() {
  const query = state.search.trim().toLowerCase();
  return state.books.filter((book) => {
    const matchesSearch = !query || [book.title, book.author, book.isbn]
      .some((value) => String(value).toLowerCase().includes(query));
    const matchesAvailability = state.availability === "all"
      || (state.availability === "available" && book.available_copies > 0)
      || (state.availability === "unavailable" && book.available_copies === 0);
    return matchesSearch && matchesAvailability;
  });
}

function renderCatalog() {
  const books = filteredBooks();
  $("#catalog-count").textContent = `${books.length} ${books.length === 1 ? "book" : "books"}`;
  $("#catalog-body").innerHTML = books.length
    ? books.map((book) => {
      let actions = "";
      if (isAdmin()) {
        actions = `<button class="row-button" type="button" data-edit-book="${book.id}">Edit</button><button class="row-button danger" type="button" data-delete-book="${book.id}">Delete</button>`;
      } else {
        actions = `<button class="row-button" type="button" data-borrow-book="${book.id}" ${book.available_copies < 1 ? "disabled" : ""}>Borrow</button>`;
      }

      return `<tr><td>${bookCell(book)}</td><td>${escapeHtml(book.isbn)}</td><td><strong>${book.available_copies}/${book.total_copies}</strong><div class="availability-bar"><span style="width:${Math.round((book.available_copies / book.total_copies) * 100)}%"></span></div></td><td>${statusBadge(book)}</td><td><span class="row-actions">${actions}</span></td></tr>`;
    }).join("")
    : '<tr><td class="empty-state" colspan="5">No books match your filters.</td></tr>';
}

function renderBooks() {
  renderStats();
  renderOverviewBooks();
  renderCatalog();
}

async function loadBooks(options = {}) {
  if (options.loading !== false) setLoading(true);
  try {
    const result = await fetchBooks();
    state.books = result.books;
    state.cacheStatus = result.cacheStatus;
    renderBooks();
  } catch (error) {
    handleError(error);
  } finally {
    setLoading(false);
  }
}

function renderHistory() {
  const active = state.records.filter((record) => !record.returned_at).length;
  const returned = state.records.length - active;
  $("#history-total").textContent = state.records.length;
  $("#history-active").textContent = active;
  $("#history-returned").textContent = returned;

  const admin = isAdmin();
  $("#history-body").innerHTML = state.records.length
    ? state.records.map((record) => {
      const book = bookById(record.book_id);
      const bookName = book ? bookCell(book) : `Book #${record.book_id}`;
      const status = record.returned_at
        ? '<span class="badge badge-neutral">Returned</span>'
        : '<span class="badge badge-warning">Active loan</span>';
      const memberCell = admin ? `<td>Member #${record.user_id}</td>` : "";
      const actionCell = admin ? "" : `<td><span class="row-actions">${record.returned_at ? "—" : `<button class="row-button" type="button" data-return-record="${record.id}">Return book</button>`}</span></td>`;
      return `<tr><td>${bookName}</td>${memberCell}<td>${formatDate(record.borrowed_at)}</td><td>${formatDate(record.returned_at)}</td><td>${status}</td>${actionCell}</tr>`;
    }).join("")
    : `<tr><td class="empty-state" colspan="${admin ? 5 : 5}">No borrowing records yet.</td></tr>`;
}

async function loadHistory(options = {}) {
  if (!state.user) return;
  if (options.loading !== false) setLoading(true);
  try {
    state.records = await fetchBorrowRecords(isAdmin());
    renderHistory();
  } catch (error) {
    handleError(error);
  } finally {
    setLoading(false);
  }
}

function openBookModal(book = null) {
  $("#book-form").reset();
  $("#book-id").value = book?.id || "";
  $("#book-modal-title").textContent = book ? "Edit Book" : "Add Book";
  $("#save-book-button").textContent = book ? "Save changes" : "Add book";
  if (book) {
    $("#book-title").value = book.title;
    $("#book-author").value = book.author;
    $("#book-isbn").value = book.isbn;
    $("#book-copies").value = book.total_copies;
  }
  showModal("#book-modal");
}

function requestDelete(bookId) {
  const book = bookById(bookId);
  if (!book) return;
  state.pendingDeleteId = book.id;
  $("#confirm-copy").textContent = `“${book.title}” will be permanently removed from the catalog.`;
  showModal("#confirm-modal");
}

function handleError(error) {
  if (error.status === 401) {
    logout(false);
    showToast("Your session expired. Please sign in again.", "error");
    return;
  }
  showToast(error.message || "Something went wrong.", "error");
}

function logout(notify = true) {
  clearToken();
  state.user = null;
  state.books = [];
  state.records = [];
  renderSession();
  switchAuthTab("login");
  if (notify) showToast("You have signed out.");
}

async function initialize() {
  if (!hasToken()) {
    renderSession();
    return;
  }
  setLoading(true);
  try {
    state.user = await getCurrentUser();
    renderSession();
    await Promise.all([loadBooks({ loading: false }), loadHistory({ loading: false })]);
  } catch (error) {
    clearToken();
    state.user = null;
    renderSession();
    handleError(error);
  } finally {
    setLoading(false);
  }
}

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);
  try {
    await login($("#login-email").value, $("#login-password").value);
    state.user = await getCurrentUser();
    renderSession();
    await Promise.all([loadBooks({ loading: false }), loadHistory({ loading: false })]);
    event.target.reset();
    showToast(`Welcome back, ${state.user.full_name.split(" ")[0]}.`);
  } catch (error) {
    handleError(error);
  } finally {
    setLoading(false);
  }
});

$("#register-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  setLoading(true);
  try {
    const email = $("#register-email").value;
    await registerAccount({
      full_name: $("#register-name").value,
      email,
      password: $("#register-password").value,
    });
    event.target.reset();
    $("#login-email").value = email;
    switchAuthTab("login");
    showToast("Account created. You can sign in now.");
  } catch (error) {
    handleError(error);
  } finally {
    setLoading(false);
  }
});

$("#book-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const bookId = Number($("#book-id").value) || null;
  const payload = {
    title: $("#book-title").value,
    author: $("#book-author").value,
    isbn: $("#book-isbn").value,
    total_copies: Number($("#book-copies").value),
  };
  setLoading(true);
  try {
    if (bookId) await updateBook(bookId, payload);
    else await createBook(payload);
    hideModal("#book-modal");
    await loadBooks({ loading: false });
    showToast(bookId ? "Book updated successfully." : "Book added to the catalog.");
  } catch (error) {
    handleError(error);
  } finally {
    setLoading(false);
  }
});

$("#confirm-action").addEventListener("click", async () => {
  if (!state.pendingDeleteId) return;
  setLoading(true);
  try {
    await deleteBook(state.pendingDeleteId);
    state.pendingDeleteId = null;
    hideModal("#confirm-modal");
    await loadBooks({ loading: false });
    showToast("Book deleted from the catalog.");
  } catch (error) {
    handleError(error);
  } finally {
    setLoading(false);
  }
});

document.addEventListener("click", async (event) => {
  const target = event.target.closest("button, a");
  if (!target) return;

  if (target.dataset.authTab) switchAuthTab(target.dataset.authTab);
  if (target.dataset.view) showView(target.dataset.view);
  if (target.hasAttribute("data-open-book-modal")) openBookModal();
  if (target.hasAttribute("data-close-modal")) hideModal("#book-modal");
  if (target.hasAttribute("data-close-confirm")) hideModal("#confirm-modal");
  if (target.dataset.editBook) openBookModal(bookById(target.dataset.editBook));
  if (target.dataset.deleteBook) requestDelete(target.dataset.deleteBook);

  if (target.dataset.togglePassword) {
    const input = $(`#${target.dataset.togglePassword}`);
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    target.textContent = showing ? "Show" : "Hide";
  }

  if (target.dataset.borrowBook) {
    target.disabled = true;
    try {
      await borrowBook(Number(target.dataset.borrowBook));
      await Promise.all([loadBooks({ loading: false }), loadHistory({ loading: false })]);
      showToast("Book borrowed successfully.");
    } catch (error) {
      handleError(error);
    } finally {
      target.disabled = false;
    }
  }

  if (target.dataset.returnRecord) {
    target.disabled = true;
    try {
      await returnBook(Number(target.dataset.returnRecord));
      await Promise.all([loadBooks({ loading: false }), loadHistory({ loading: false })]);
      showToast("Book returned successfully.");
    } catch (error) {
      handleError(error);
    } finally {
      target.disabled = false;
    }
  }
});

$("#catalog-search").addEventListener("input", (event) => {
  state.search = event.target.value;
  $("#global-search-input").value = event.target.value;
  renderCatalog();
});

$("#global-search-input").addEventListener("input", (event) => {
  state.search = event.target.value;
  $("#catalog-search").value = event.target.value;
  renderCatalog();
  if (event.target.value) showView("books");
});

$("#availability-filter").addEventListener("change", (event) => {
  state.availability = event.target.value;
  renderCatalog();
});

$("#refresh-books").addEventListener("click", () => loadBooks());
$("#refresh-history").addEventListener("click", () => loadHistory());
$("#logout-button").addEventListener("click", () => logout());
$("#menu-button").addEventListener("click", () => $("#sidebar").classList.toggle("open"));

document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    $("#global-search-input").focus();
  }
  if (event.key === "Escape") {
    hideModal("#book-modal");
    hideModal("#confirm-modal");
    $("#sidebar").classList.remove("open");
  }
});

initialize();
