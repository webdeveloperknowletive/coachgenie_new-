import enCommon from "../locales/en/common.json";
import hiCommon from "../locales/hi/common.json";
import mrCommon from "../locales/mr/common.json";
import { type SupportedLanguage, TRANSLATIONS, translate } from "./translations";

export const defaultNS = "common";
export const resources = {
  en: { common: enCommon },
  hi: { common: hiCommon },
  mr: { common: mrCommon },
} as const;

class I18nManager {
  private currentLanguage: SupportedLanguage = "en";
  private listeners: Array<(lang: SupportedLanguage) => void> = [];

  get language(): SupportedLanguage {
    return this.currentLanguage;
  }

  changeLanguage(lang: SupportedLanguage): Promise<void> {
    this.currentLanguage = lang;
    this.listeners.forEach((fn) => fn(lang));
    return Promise.resolve();
  }

  t(key: string): string {
    return translate(key, this.currentLanguage);
  }

  onLanguageChanged(fn: (lang: SupportedLanguage) => void): () => void {
    this.listeners.push(fn);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== fn);
    };
  }
}

export const i18n = new I18nManager();
export default i18n;

export * from "./translations";
export * from "./transliterator";