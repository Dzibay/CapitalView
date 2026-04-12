import { ShieldCheck, Lock, Zap, Eye } from 'lucide-vue-next'
import * as landingData from '../content/home/landingData'

const ICONS = {
  ShieldCheck,
  Lock,
  Zap,
  Eye,
}

function mapIcons(items) {
  return items.map((item) => ({
    ...item,
    icon: ICONS[item.icon],
  }))
}

export function useLandingContent() {
  return {
    integrationBullets: landingData.integrationBullets,
    comingSoonBrokers: landingData.comingSoonBrokers,
    steps: landingData.steps,
    securityTabs: mapIcons(landingData.securityTabs),
    pricingFeatures: landingData.pricingFeatures,
    faq: landingData.faq,
  }
}
