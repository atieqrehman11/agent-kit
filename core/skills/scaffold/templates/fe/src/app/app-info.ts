/** The app's own identity, in one place.
 *
 * Not inlined into JSX: these are the two values the scaffold substitutes, and a
 * token sitting inside wrapped prose changes the line length when it is
 * replaced — which changes where Prettier wants to wrap, which fails
 * `npm run format:check` in a repo nobody has touched yet. A string on its own
 * line has no wrapping to change. */
export const APP_NAME = 'TPLVAR_DISPLAY_NAME'
export const APP_DESCRIPTION = 'TPLVAR_DESCRIPTION'
