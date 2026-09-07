import type {Metadata} from 'next';
import './globals.css';
export const metadata:Metadata={title:'糖果防線｜3D 防空守衛',description:'裝配武器、建立防線，守住糖果城市。可在瀏覽器遊玩的第一人稱 3D 空地防守遊戲。'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="zh-Hant"><body>{children}</body></html>}
