import { isRetryableError, retryDelay, retryRequest, RETRY_MAX } from './apiAuth';

const err = (config: any, status?: number) => ({ config, response: status ? { status } : undefined });

test('retries network errors and 5xx gateway errors on GET only', () => {
  expect(isRetryableError(err({ method: 'get' }))).toBe(true);
  expect(isRetryableError(err({ method: 'get' }, 503))).toBe(true);
  expect(isRetryableError(err({ method: 'get' }, 404))).toBe(false);
  expect(isRetryableError(err({ method: 'post' }))).toBe(false);
  expect(isRetryableError(err({ method: 'post', retryable: true }))).toBe(true);
});

test('backoff grows and attempts are capped', async () => {
  expect(retryDelay(2)).toBe(retryDelay(1) * 2);
  const e = err({ method: 'get', __retryCount: RETRY_MAX });
  await expect(retryRequest(e)).rejects.toBe(e);
});
