import { apiRequest, jsonOptions } from "./api.js";

export async function fetchBooks() {
  const { data, headers } = await apiRequest("/books");
  return {
    books: data,
    cacheStatus: headers.get("X-Cache") || "BYPASS",
  };
}

export async function createBook(book) {
  const { data } = await apiRequest("/books", jsonOptions("POST", book));
  return data;
}

export async function updateBook(bookId, book) {
  const { data } = await apiRequest(
    `/books/${bookId}`,
    jsonOptions("PUT", book),
  );
  return data;
}

export async function deleteBook(bookId) {
  await apiRequest(`/books/${bookId}`, { method: "DELETE" });
}
