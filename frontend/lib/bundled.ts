import stages from '../../data/aftermath_steps.json';
import faqs from '../../data/faqs.json';
import resources from '../../data/resources.json';
import type { Stage, Faq, Resource } from './types';
export const BUNDLED_STAGES = stages as Stage[];
export const BUNDLED_FAQS = faqs as Faq[];
export const BUNDLED_RESOURCES = resources as Resource[];

