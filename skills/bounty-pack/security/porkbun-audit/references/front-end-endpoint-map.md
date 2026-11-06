# Front-end endpoint map (from jsluice on skaboink.js + support-widget.js + webauthn*.js)

Non-API-v3 surface on porkbun.com. All `/api/domains/*` and authenticated `/api/user/*` return `{"error":1,"message":"Not logged in."}` (200) or 401 when unauthenticated — auth is consistently enforced, not a bug.

## /api/domains/* (domain management, auth-gated)
getChecks (UNAUTH — domain availability/aftermarket check; returns {settings,results,pending})
clearChecks, getDomainManagementDetails, getDomainManagementDetailsSlow, getDomainManagementDetailsUi,
getDomainDNS, deleteDomainDNS, addDomainLabel, applyDomainLabels, removeDomainLabel, createNewDomainLabel,
addUserSetting, changeIPSTag, configureServiceDNS, hostingAutoRenewSetting,
selfServeRegistrationRefund, selfServeRenewalRefund, toggleCloudflare, toggleCloudflareDomainDNS.

## /api/user/* — CART (anonymous via cartId cookie, but domain items need login)
getCart (unauth, returns {status,cart}), addToCart (payload = `cart[0][type]=registration&cart[0][domain]=D` jQuery-bracket serialization; domain/registration items -> "You must be logged in"), removeCartItem, emptyCart,
updateCartAmount ({cartId,amount} = ACCOUNT-CREDIT topup min $10, server-validated), updateCartCount, updateCartDuration ({cartId,duration,level,domain,all,type}), updateCartPlan, applyCartCoupon ({couponCode}).

## /api/user/* — 2FA / webauthn (auth-gated)
getTwoFactorKey, resetTwoFactorKey, checkTwoFAAuth, getTOTPQRCode/{user}, getGenericQRCode/, login_passkey (webauthn), webauthnregister, getWidgetCode.

## /api/user/* — money / billing (auth-gated)
buyAccountCreditAch, setupAchForAccount, setupAchIntent, showConfigureAchModal, verifyAch ({depositOne,depositTwo}), deleteAch.

## /api/user/* — email / marketplace / misc (auth-gated)
sendAccountEmailVerification, sendAccountEmailBackupVerification, cancelPendingEmailVerification, cancelPendingEmailBackupVerification, setupEmailAddress,
checkMarketplaceDomain ({domain}), saveToWishList ({itemId}), clearSavedCoupons, resetService, cookiePrivacySave/OptIn/OptOut, cookieSupportOptIn/OptOut.

## /tools/* (AI support — see SKILL.md; action endpoints 401, RAG support_chat_api unauth)
## Anti-bot unauth: /tools/porkCaptchaIssue, /tools/porkCaptchaChallenge, /tools/checkCcaptcha, /api/user/pbSimpleHumanCheckerClick_20230305 (GET -> {code: sha256}, the "I'm not a robot" challenge), /api/user/init (sets PRB).

## /account/refundRenewalConfirmation?code=  (money link — needs account+renewal; code predictability not tested)
## jsluice `secrets` over all 11 bundles = ZERO secrets leaked.