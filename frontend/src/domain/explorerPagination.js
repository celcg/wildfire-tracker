export const EXPLORER_PAGE_SIZE = 20;

export function getPageForIndex(index, pageSize = EXPLORER_PAGE_SIZE) {
  if (!Number.isInteger(index) || index < 0) {
    return 1;
  }

  return Math.floor(index / pageSize) + 1;
}

export function paginate(items, requestedPage, pageSize = EXPLORER_PAGE_SIZE) {
  const totalItems = items.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const page = Math.min(Math.max(Number(requestedPage) || 1, 1), totalPages);
  const startIndex = (page - 1) * pageSize;

  return {
    items: items.slice(startIndex, startIndex + pageSize),
    page,
    pageSize,
    startIndex,
    totalItems,
    totalPages,
  };
}
