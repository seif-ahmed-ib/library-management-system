import { apiRequest, jsonOptions } from "./api.js";

export async function fetchBorrowRecords(isAdmin) {
  const path = isAdmin ? "/borrows" : "/borrows/me/history";
  const { data } = await apiRequest(path);
  return data;
}

export async function borrowBook(bookId) {
  const { data } = await apiRequest(
    "/borrows",
    jsonOptions("POST", { book_id: bookId }),
  );
  return data;
}

export async function returnBook(recordId) {
  const { data } = await apiRequest(`/borrows/${recordId}/return`, {
    method: "POST",
  });
  return data;
}
