"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendRow } from "@/lib/types";

const COLORS = ["#197556", "#77ab8b", "#d9ac63", "#7199af"];

export function TrendChart({ rows }: { rows: TrendRow[] }) {
  const keywords = useMemo(
    () => [...new Set(rows.map((row) => row.keyword))].sort(),
    [rows],
  );
  const periods = useMemo(() => {
    const indexed = new Map<string, Record<string, string | number>>();
    for (const row of rows) {
      const found = indexed.get(row.reference_date) ?? {
        date: row.reference_date,
      };
      found[row.keyword] = Number(row.ratio);
      indexed.set(row.reference_date, found);
    }
    return [...indexed.values()].sort((a, b) =>
      String(a.date).localeCompare(String(b.date)),
    );
  }, [rows]);

  if (!rows.length)
    return <p className="trend-empty">검색 관심도 데이터가 아직 없습니다.</p>;
  return (
    <>
      <div
        className="h-72 w-full"
        role="img"
        aria-label={`전국 NAVER 검색 관심도: ${keywords.join(", ")} ${periods.length}개월 추이. 아래 관측값 표에서도 확인할 수 있습니다.`}
      >
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <LineChart
            data={periods}
            margin={{ top: 8, right: 14, left: -24, bottom: 4 }}
          >
            <CartesianGrid
              strokeDasharray="3 5"
              stroke="#e7ede7"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tickFormatter={(value: string) => value.slice(2, 7)}
              tickLine={false}
              axisLine={false}
              fontSize={10}
              stroke="#91a193"
              minTickGap={25}
            />
            <YAxis
              domain={[0, 100]}
              tickLine={false}
              axisLine={false}
              fontSize={10}
              stroke="#91a193"
            />
            <Tooltip
              labelFormatter={(value) =>
                `${String(value).slice(0, 7)} · 전국 상대 검색 관심도`
              }
              formatter={(value) => [
                Number(value).toLocaleString("ko-KR", {
                  maximumFractionDigits: 2,
                }),
                undefined,
              ]}
              contentStyle={{
                borderRadius: 9,
                border: "1px solid #dfe9df",
                fontSize: 11,
              }}
            />
            <Legend
              iconType="circle"
              iconSize={6}
              wrapperStyle={{ fontSize: 10, paddingTop: 14 }}
            />
            {keywords.map((keyword, index) => (
              <Line
                key={keyword}
                type="monotone"
                dataKey={keyword}
                stroke={COLORS[index % COLORS.length]}
                strokeWidth={2}
                dot={false}
                connectNulls={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details className="trend-table">
        <summary>관측값 표로 보기</summary>
        <div className="table-scroll">
          <table>
            <caption className="sr-only">
              전국 NAVER 월별 키워드 상대 검색 관심도
            </caption>
            <thead>
              <tr>
                <th scope="col">관측월</th>
                {keywords.map((keyword) => (
                  <th key={keyword} scope="col">
                    {keyword}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {periods.map((period) => (
                <tr key={period.date}>
                  <th scope="row">{String(period.date).slice(0, 7)}</th>
                  {keywords.map((keyword) => (
                    <td key={keyword}>
                      {period[keyword] == null
                        ? "—"
                        : Number(period[keyword]).toLocaleString("ko-KR", {
                            maximumFractionDigits: 2,
                          })}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}
