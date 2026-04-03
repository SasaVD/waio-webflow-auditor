import { useNavigate, useSearchParams } from 'react-router';
import { AuditHistory } from '../components/AuditHistory';

export function HistoryPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const url = searchParams.get('url') || '';

  return <AuditHistory url={url} onBack={() => navigate('/')} />;
}
