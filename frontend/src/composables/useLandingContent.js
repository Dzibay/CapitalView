import {
  BarChart3,
  RefreshCw,
  Coins,
  FileSpreadsheet,
  Smartphone,
  Calculator,
  Lock,
  Zap
} from 'lucide-vue-next'
import * as landingData from '../content/landingData'

const ICONS = {
  BarChart3,
  RefreshCw,
  Coins,
  FileSpreadsheet,
  Smartphone,
  Calculator,
  Lock,
  Zap
}

function mapIcons(items) {
  return items.map((item) => ({
    ...item,
    icon: ICONS[item.icon]
  }))
}

/**
 * Единая точка данных для лендинга: тексты из content/ + иконки Lucide.
 */
export function useLandingContent() {
  return {
    painPoints: mapIcons(landingData.painPoints),
    features: mapIcons(landingData.features),
    steps: landingData.steps,
    integrationFeatures: mapIcons(landingData.integrationFeatures),
    comingSoonBrokers: landingData.comingSoonBrokers,
    pricing: landingData.pricing,
    testimonials: landingData.testimonials,
    faq: landingData.faq
  }
}
