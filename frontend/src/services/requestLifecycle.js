export function supersedeRequest(activeRequest, nextRequest = null) {
  activeRequest.current?.abort();
  activeRequest.current = nextRequest;
}

export function isCurrentRequest(activeRequest, request) {
  return activeRequest.current === request && !request.signal.aborted;
}

export function shouldClearVisibleData(loadedDays, targetDays) {
  return loadedDays !== targetDays;
}
