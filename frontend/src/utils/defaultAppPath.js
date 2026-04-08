/** Куда вести авторизованного пользователя по умолчанию (после входа / OAuth). */
export function defaultAuthenticatedPath(user) {
  if (user?.is_admin) return '/admin'
  return '/dashboard'
}
