import { getAppCheckToken } from "./firebaseAppCheck.js";
import { getClientId } from "./clientIdentity.js";

export const CLIENT_ID_HEADER = "X-Client-ID";
export const APP_CHECK_HEADER = "X-Firebase-AppCheck";

export async function buildRequestSecurityHeaders({
  clientId = getClientId(),
  tokenProvider = getAppCheckToken,
} = {}) {
  const headers = { [CLIENT_ID_HEADER]: clientId };
  const appCheckToken = await tokenProvider();
  if (appCheckToken) {
    headers[APP_CHECK_HEADER] = appCheckToken;
  }
  return headers;
}
