import { DatabaseSync } from 'node:sqlite';
import { readdirSync, readFileSync } from 'node:fs';
export function testDb() {
  const sql = new DatabaseSync(':memory:');
  for (const f of readdirSync('drizzle')
    .filter((x) => x.endsWith('.sql'))
    .sort())
    sql.exec(readFileSync('drizzle/' + f, 'utf8'));
  const wrap = (query, values = []) => ({
    bind(...v) {
      return wrap(query, v);
    },
    async first() {
      return sql.prepare(query).get(...values) ?? null;
    },
    async all() {
      return { results: sql.prepare(query).all(...values) };
    },
    async run() {
      const r = sql.prepare(query).run(...values);
      return { meta: { changes: Number(r.changes) } };
    },
    query,
    values,
  });
  return {
    sql,
    prepare: wrap,
    async batch(rows) {
      sql.exec('BEGIN');
      try {
        const result = rows.map((r) => ({
          meta: {
            changes: Number(sql.prepare(r.query).run(...r.values).changes),
          },
        }));
        sql.exec('COMMIT');
        return result;
      } catch (e) {
        sql.exec('ROLLBACK');
        throw e;
      }
    },
  };
}
