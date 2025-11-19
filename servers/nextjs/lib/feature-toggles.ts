/**
 * Feature toggles for controlling UI page visibility
 */

export const FEATURE_TOGGLES = {
  // Page visibility controls
  SHOW_DASHBOARD: process.env.NEXT_PUBLIC_SHOW_DASHBOARD !== 'false',
  SHOW_SETTINGS: process.env.NEXT_PUBLIC_SHOW_SETTINGS !== 'false',
  SHOW_HEADER_NAV: process.env.NEXT_PUBLIC_SHOW_HEADER_NAV !== 'false',
  SHOW_LOGO_LINK: process.env.NEXT_PUBLIC_SHOW_LOGO_LINK !== 'false',
  SHOW_ANNOUNCEMENT: process.env.NEXT_PUBLIC_SHOW_ANNOUNCEMENT !== 'false',
} as const;

export type FeatureToggleKey = keyof typeof FEATURE_TOGGLES;
