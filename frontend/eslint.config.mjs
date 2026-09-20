import { FlatCompat } from '@eslint/eslintrc';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });
export default [
  { ignores: ['.next/**', 'public/service-worker.js', 'node_modules/**', '.npm-cache/**'] },
  ...compat.extends('next/core-web-vitals', 'next/typescript'),
];
