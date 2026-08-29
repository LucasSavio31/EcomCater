// Barrel CLIENT-SAFE. Nada de `server-only` aqui (get-config e scripts são
// importados direto pelos server components que os usam — ver layout.tsx).
export { AnalyticsRouteTracker } from './route-tracker';
export { track, trackPageView, identify, type IdentifyData } from './tracker';
export { cartToTrackItems, orderToTrackItems } from './cart-items';
export {
  DISABLED_ANALYTICS,
  type AnalyticsConfig,
  type TrackItem,
  type TrackEvent,
} from './types';
