import { DatabaseSync } from 'node:sqlite';
import { readdirSync, readFileSync } from 'node:fs';
export function testDb() {
  const sql = new DatabaseSync(':memory:');
  const metrics = { roundTrips: 0 };
  for (const f of readdirSync('drizzle')
    .filter((x) => x.endsWith('.sql'))
    .sort())
    sql.exec(readFileSync('drizzle/' + f, 'utf8'));
  const wrap = (query, values = []) => ({
    bind(...v) {
      return wrap(query, v);
    },
    async first() {
      metrics.roundTrips++;
      return sql.prepare(query).get(...values) ?? null;
    },
    async all() {
      metrics.roundTrips++;
      return { results: sql.prepare(query).all(...values) };
    },
    async run() {
      metrics.roundTrips++;
      const r = sql.prepare(query).run(...values);
      return { meta: { changes: Number(r.changes) } };
    },
    query,
    values,
  });
  return {
    sql,
    metrics,
    prepare: wrap,
    async batch(rows) {
      metrics.roundTrips++;
      sql.exec('BEGIN');
      try {
        const result = rows.map((r) => {
          const statement = sql.prepare(r.query);
          if (statement.columns().length)
            return {
              results: statement.all(...r.values),
              meta: { changes: 0 },
            };
          return {
            meta: { changes: Number(statement.run(...r.values).changes) },
          };
        });
        sql.exec('COMMIT');
        return result;
      } catch (e) {
        sql.exec('ROLLBACK');
        throw e;
      }
    },
  };
}
